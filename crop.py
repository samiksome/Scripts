#!/usr/bin/env python3

"""A script to crop an image in an intelligent manner trying to keep the most important parts.

Given an image the script currently maximises the crop location w.r.t. image gradients. If requested the image is first
resized to fit one crop dimension.
"""

import argparse
import os
from shutil import copy

import cv2 as cv
import numpy as np
from PIL import Image


def gradient_crop(img, crop_size):
    """Crop an image using gradients as importance features.

    Paramters
    ---------
    img : numpy.ndarray
        Numpy array of the image with shape (h, w, c), dtype uint8 and values between 0-255.
    crop_size : tuple(int, int)
        Tuple specifying the crop size as (w, h).

    Returns
    -------
    numpy.ndarray
        Numpy array of the cropped image.
    """
    crop_width, crop_height = crop_size

    # Calculate laplacian and integral image.
    laplacian = np.absolute(cv.Laplacian(cv.cvtColor(img, cv.COLOR_BGR2GRAY), cv.CV_64F))
    integral = cv.integral(laplacian)

    # Calculate max sum window.
    max_sum = -1
    max_i = 0
    max_j = 0
    for i in range(1, integral.shape[0]-crop_height+1):
        for j in range(1, integral.shape[1]-crop_width+1):
            crop_sum = integral[i+crop_height-1, j+crop_width-1] - integral[i-1, j+crop_width-1] - \
                integral[i+crop_height-1, j-1] + integral[i-1, j-1]
            if crop_sum > max_sum:
                max_sum = crop_sum
                max_i = i-1
                max_j = j-1

    # Return cropped image.
    return img[max_i:max_i+crop_height, max_j:max_j+crop_width]


def crop(img_path, crop_size, fit=False, out_file=None):
    """Crops an image intelligently by looking at image gradients and keeping the crop window with the largest sum of
    such gradients.

    Parameters
    ----------
    img_path : str
        Image to crop.
    crop_size : tuple(int, int)
        Tuple specifying the crop size as (w, h).
    fit : bool, optional
        Resize the image to fit one crop dimension if True. (default=False)
    out_file : str, optional
        Output file path. (default=None)
    """

    crop_width, crop_height = crop_size

    with Image.open(img_path, 'r') as img:
        width, height = img.size

        # Validate crop size.
        if crop_width > width or crop_height > height:
            print('Crop size must be smaller than image.')
            return

        # Resize if fit is True.
        if fit:
            aspect_ratio = float(width) / height
            crop_ratio = float(crop_width) / crop_height

            if aspect_ratio >= crop_ratio:
                new_width = int(aspect_ratio * crop_height)
                new_height = crop_height
            else:
                new_width = crop_width
                new_height = int(1.0 / aspect_ratio * crop_width)

            img = img.resize((new_width, new_height), resample=Image.LANCZOS)
            img.save(os.path.join(os.path.dirname(img_path), os.path.basename(img_path)+'.tmp'), format='PNG')
        else:
            copy(img_path, os.path.join(os.path.dirname(img_path), os.path.basename(img_path)+'.tmp'))

    # Open image using OpenCV and crop it.
    img = cv.imread(os.path.join(os.path.dirname(img_path), os.path.basename(img_path)+'.tmp'), cv.IMREAD_COLOR)
    cropped_img = gradient_crop(img, crop_size)

    # Write output image
    if out_file is None:
        cv.imwrite(os.path.join(os.path.dirname(img_path), os.path.splitext(os.path.basename(img_path))
                                [0]+'_cropped.png'), cropped_img)
    else:
        cv.imwrite(out_file, cropped_img)

    # Clean up
    os.remove(os.path.join(os.path.dirname(img_path), os.path.basename(img_path)+'.tmp'))


def main():
    """Main function for the script."""
    parser = argparse.ArgumentParser()
    parser.add_argument('img_path', help='Image to crop')
    parser.add_argument('crop_size', help='Crop size as WxH')
    parser.add_argument('-f', '--fit', help='Resize image to fit one crop dimension', action='store_true')
    parser.add_argument('-o', '--out_file', help='Output file')
    args = parser.parse_args()

    crop_size = (int(args.crop_size.split('x')[0]), int(args.crop_size.split('x')[1]))
    crop(args.img_path, crop_size, args.fit, args.out_file)


if __name__ == '__main__':
    main()
