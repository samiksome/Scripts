#!/usr/bin/env python3

"""This script takes a directory as input and produces a CBZ file as output.

Given a directory with images, it first checks all images for supported formats and possible corrupted images. Once
checked all images are converted to JPEG format with specified quality factor, if they are larger than specified
resolution they are scaled down as well. The images are optionally renamed and packed into a zip file.
"""

import argparse
import os
from shutil import copy
from zipfile import ZipFile

from PIL import Image
from tqdm import tqdm

SUPPORTED_FORMATS = ['JPEG', 'PNG', 'GIF', 'WEBP']


def is_animated(img):
    """Checks whether an image is animated or not.

    Parameters
    ----------
    img : PIL.Image
        Image.

    Returns
    -------
    bool
        Whether image is animated or not.
    """
    try:
        img.seek(1)
        return True
    except EOFError:
        return False


def resize(img, size):
    """Resize an image.

    Parameters
    ----------
    img : PIL.Image
        Image to resize.
    size : tuple(int, int)
        Size to resize to as (w, h) tuple.

    Returns
    -------
    img : PIL.Image
        Resized image.
    """
    img = img.convert('RGB')
    img = img.resize(size, resample=Image.LANCZOS)

    return img


def composite(img):
    """Alpha composite a RGBA image over a black background.

    Parameters
    ----------
    img : PIL.Image
        Image to composite.

    Returns
    -------
    img : PIL.Image
        Composite image.
    """
    img = img.convert('RGBA')
    background_img = Image.new('RGBA', img.size, color=(0, 0, 0))
    img = Image.alpha_composite(background_img, img)
    img = img.convert('RGB')

    return img


def get_scale(inv_aspect):
    """Return the image scale based on aspect ratio as a float.

    Parameters
    ----------
    inv_aspect : float
        Inverse aspect ratio of the image (h/w).

    Returns
    -------
    float
        Image scale.
    """
    inv_aspect /= 1.5
    if inv_aspect-int(inv_aspect) < 0.25:
        return int(inv_aspect)+0.0
    if inv_aspect-int(inv_aspect) < 0.75:
        return int(inv_aspect)+0.5
    return int(inv_aspect)+1.0


def process_jpeg(img_file, out_file, quality=95, scale_down=False, new_size=None):
    """Process a JPEG image.

    Parameters
    ----------
    img_file : str
        Image file.
    out_file : str
        Output file.
    quality : int, optional
        JPEG quality. (default=95)
    scale_down : bool, optional
        Whether to scale image or not. (default=False)
    new_size : tuple(int, int), optional
        New size if scaling is needed. (default=None)
    """
    if scale_down:
        with Image.open(img_file, 'r') as img:
            img = resize(img, new_size)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)
    else:
        copy(img_file, f'{out_file}.jpg')


def process_png(img_file, out_file, quality=95, scale_down=False, new_size=None):
    """Process a PNG image.

    Parameters
    ----------
    img_file : str
        Image file.
    out_file : str
        Output file.
    quality : int, optional
        JPEG quality. (default=95)
    scale_down : bool, optional
        Whether to scale image or not. (default=False)
    new_size : tuple(int, int), optional
        New size if scaling is needed. (default=None)
    """
    with Image.open(img_file, 'r') as img:
        if scale_down:
            img = composite(img)
            img = resize(img, new_size)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)
        else:
            img = composite(img)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)


def process_gif(img_file, out_file, quality=95, scale_down=False, new_size=None):
    """Process a GIF image.

    Parameters
    ----------
    img_file : str
        Image file.
    out_file : str
        Output file.
    quality : int, optional
        JPEG quality. (default=95)
    scale_down : bool, optional
        Whether to scale image or not. (default=False)
    new_size : tuple(int, int), optional
        New size if scaling is needed. (default=None)
    """
    with Image.open(img_file, 'r') as img:
        if scale_down:
            img = composite(img)
            img = resize(img, new_size)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)
        else:
            img = composite(img)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)


def process_webp(img_file, out_file, quality=95, scale_down=False, new_size=None):
    """Process a WEBP image.

    Parameters
    ----------
    img_file : str
        Image file.
    out_file : str
        Output file.
    quality : int, optional
        JPEG quality. (default=95)
    scale_down : bool, optional
        Whether to scale image or not. (default=False)
    new_size : tuple(int, int), optional
        New size if scaling is needed. (default=None)
    """
    with Image.open(img_file, 'r') as img:
        if scale_down:
            img = composite(img)
            img = resize(img, new_size)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)
        else:
            img = composite(img)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)


def check_files(file_list):
    """Check all files and return supported image files and non-supported files.

    Parameters
    ----------
    file_list : list[str]
        List of files.

    Returns
    -------
    img_files : dict
        Dictionary of all supported image files.
    bad_files : list[tuple(str, str)]
        List of bad files and reasons why they are bad.
    """
    img_files = []
    bad_files = []
    progress_bar = tqdm(file_list, bar_format='Checking all files |{bar:20}| {n_fmt}/{total_fmt}')
    for file_path in progress_bar:
        try:
            with Image.open(file_path, 'r') as img:
                img.load()
                animated = is_animated(img)
                if img.format not in SUPPORTED_FORMATS:
                    bad_files.append((file_path, 'Unsupported image format.'))
                elif animated:
                    bad_files.append((file_path, 'Animated/multi-frame images not supported.'))
                else:
                    img_files.append({'path': file_path, 'format': img.format, 'size': img.size})
        except IOError:
            bad_files.append((file_path, 'Error in reading as image.'))

    return img_files, bad_files


def find_duplicates(file_list):
    """Checks if any files share the same basename (not case sensitive).

    Parameters
    ----------
    files : list[str]
        List of files.

    Returns
    -------
    dup_file_list : list[list[str]]
        List of lists of duplicate files.
    """
    # Normalize all path names and add them to a dictionary.
    file_dict = {}
    for file_path in file_list:
        key = os.path.splitext(os.path.basename(file_path))[0].lower()
        if key not in file_dict:
            file_dict[key] = []
        file_dict[key].append(file_path)

    # Check for duplicates.
    dup_file_list = []
    for key in sorted(file_dict.keys()):
        if len(file_dict[key]) > 1:
            dup_file_list.append(sorted(file_dict[key]))

    return dup_file_list


def make_cbz(dir_path, h_res=3200, quality=95, no_rename=False, delete=False):
    """Make a cbz from a directory.

    dir_path : str
        Path to directory.
    h_res : int, optional
        Maximum horizontal resolution. (default=3200)
    quality : int, optional
        JPEG quality. (default=95)
    no_rename : bool, optional
        Don't rename files if True. (default=False)
    delete : bool, optional
        Delete original files and directory if True. (default=False)
    """
    # Check if output file is already present.
    out_zip_file = os.path.join(os.path.dirname(dir_path), f'{os.path.basename(dir_path)}.cbz')
    if os.path.exists(out_zip_file):
        while True:
            overwrite = input('Output file already exists. Overwrite? [y/N] ')
            if overwrite in ['y', 'Y']:
                break
            if overwrite in ['n', 'N', '']:
                print('Not creating cbz.')
                return

    # Get all files.
    file_list = [os.path.join(dir_path, f) for f in sorted(os.listdir(dir_path))]

    # Check for duplicates.
    dup_file_list = find_duplicates(file_list)

    if dup_file_list:
        print('Duplicate files present.')
        for dup_files in dup_file_list:
            print(f"\t{', '.join([os.path.basename(f) for f in dup_files])}")
        return

    # Check if all files are supported image formats or not.
    img_files, bad_files = check_files(file_list)

    if bad_files:
        print(f'Found {len(bad_files)} bad files.')
        for bad_file in bad_files:
            print(f'\t{os.path.basename(bad_file[0])}: {bad_file[1]}')
        return

    # Create temp directory.
    os.mkdir(os.path.join(dir_path, 'tmp'))

    # Process all images.
    progress_bar = tqdm(img_files, bar_format='Processing images  |{bar:20}| {n_fmt}/{total_fmt}')
    out_idx_format = '{:0' + str(max(2, len(str(len(img_files) + 1)))) + 'd}'
    for idx, img_file in enumerate(progress_bar):
        width, height = img_file['size']
        scale = max(get_scale(float(height)/float(width)), 1.0)  # scale >= 1.0
        new_height = round(h_res * scale)
        new_width = round(float(width)/float(height)*float(new_height))
        new_size = (new_width, new_height)
        scale_down = height > new_height

        if no_rename:
            out_name = os.path.splitext(os.path.basename(img_file['path']))[0]
        else:
            out_name = out_idx_format.format(idx + 1)
        out_file = os.path.join(dir_path, 'tmp', out_name)

        if img_file['format'] == 'JPEG':
            process_jpeg(img_file['path'], out_file, quality, scale_down, new_size)
        elif img_file['format'] == 'PNG':
            process_png(img_file['path'], out_file, quality, scale_down, new_size)
        elif img_file['format'] == 'GIF':
            process_gif(img_file['path'], out_file, quality, scale_down, new_size)
        elif img_file['format'] == 'WEBP':
            process_webp(img_file['path'], out_file, quality, scale_down, new_size)

    # Create zip file.
    img_files = [os.path.join(dir_path, 'tmp', f) for f in sorted(os.listdir(os.path.join(dir_path, 'tmp')))]
    print('Creating cbz ...')
    with ZipFile(out_zip_file, 'w') as zipf:
        for img_file in img_files:
            zipf.write(img_file, arcname=os.path.basename(img_file))

    # Clean up.
    for img_file in img_files:
        os.remove(img_file)
    os.rmdir(os.path.join(dir_path, 'tmp'))

    # If requested, delete original files and directory.
    if delete:
        print('Deleting original files and directory ...')
        for file_path in file_list:
            os.remove(file_path)
        os.rmdir(dir_path)

    print('Done.')


def main():
    """Main function for the script which takes directories as input and converts them to CBZs."""
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('dir_paths', help='Directory/directories containing the images', nargs='+')
    parser.add_argument('-r', '--resolution', help='Maximum horizontal resolution', type=int, default=3200)
    parser.add_argument('-q', '--quality', help='Quality parameter for JPEG (0-100)', type=int, default=95)
    parser.add_argument('-n', '--no_rename', help="Don't rename files", action='store_true')
    parser.add_argument('-d', '--delete', help='Delete original files', action='store_true')
    args = parser.parse_args()

    # Run make_cbz for each directory.
    for dir_path in args.dir_paths:
        dir_path = os.path.normpath(dir_path)
        print(f'Processing {dir_path} ...')
        make_cbz(dir_path, args.resolution, args.quality, args.no_rename, args.delete)


if __name__ == '__main__':
    main()
