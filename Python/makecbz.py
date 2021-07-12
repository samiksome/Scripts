#!/usr/bin/env python3

"""This script takes a directory as input and produces a CBZ file as output.

Given a directory with images, it first checks all images for supported formats and possible corrupted images. Once
checked all images are converted to JPEG format with specified quality factor, if they are larger than specified
resolution they are scaled down as well. The images are optionally renamed and packed into a zip file.
"""

import argparse
import os
from shutil import copy, move
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


def resize_alpha(img, size):
    """Resize an image with alpha channel.

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
    img = img.convert('RGBA')
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


def process_image(img_file, out_file, jpeg=False, png=False, quality=None, scale_down=False, new_size=None):
    """Process a image.

    Parameters
    ----------
    img_file : dict
        Image file.
    out_file : str
        Output file.
    jpeg : bool, optional
        Convert images to JPEG if True. (default=False)
    png : bool, optional
        Convert images to PNG if True. (default=False)
    quality : int, optional
        JPEG quality or PNG compression. (default=None)
    scale_down : bool, optional
        Whether to scale image or not. (default=False)
    new_size : tuple(int, int), optional
        New size if scaling is needed. (default=None)
    """
    # Copy file without any changes for valid cases.
    if img_file['format'] == 'JPEG' and not png and not scale_down:
        copy(img_file['path'], f'{out_file}.jpg')
    elif img_file['format'] == 'PNG' and not jpeg and not scale_down:
        copy(img_file['path'], f'{out_file}.png')
    elif img_file['format'] == 'GIF' and not jpeg and not png and not scale_down:
        copy(img_file['path'], f'{out_file}.gif')
    elif img_file['format'] == 'WEBP' and not jpeg and not png and not scale_down:
        copy(img_file['path'], f'{out_file}.webp')
    # Output image as JPEG.
    elif jpeg:
        with Image.open(img_file, 'r') as img:
            img = composite(img)
            if scale_down:
                img = resize(img, new_size)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)
    # Output image as PNG.
    elif png:
        with Image.open(img_file, 'r') as img:
            if scale_down:
                img = resize_alpha(img, new_size)
            img.save(f'{out_file}.png', compress_level=quality)
    # Output image as same format.
    elif img_file['format'] == 'JPEG':
        with Image.open(img_file, 'r') as img:
            img = resize(img, new_size)
            img.save(f'{out_file}.jpg', quality=quality, optimize=True)
    elif img_file['format'] == 'PNG':
        with Image.open(img_file, 'r') as img:
            img = resize_alpha(img, new_size)
            img.save(f'{out_file}.png', compress_level=quality)
    elif img_file['format'] == 'GIF':
        with Image.open(img_file, 'r') as img:
            img = resize_alpha(img, new_size)
            img.save(f'{out_file}.gif')
    elif img_file['format'] == 'WEBP':
        with Image.open(img_file, 'r') as img:
            img = resize_alpha(img, new_size)
            img.save(f'{out_file}.webp')
    # Should not be reachable.
    else:
        print('Error: Unreachable state')
        return


def merge_subdirs(dir_path):
    """Merge images in sub-directories after verifying them.

    Parameters
    ----------
    dir_path : str
        Path to directory.

    Returns
    -------
    bool
        True if merge is successfull, False otherwise.
    """
    # Get list of sub-directories.
    subdirs = [os.path.join(dir_path, d) for d in sorted(os.listdir(dir_path))
               if os.path.isdir(os.path.join(dir_path, d))]

    # Scan sub-directories.
    max_imgs = 0
    for subdir in subdirs:
        # Get all files.
        file_list = [os.path.join(subdir, f) for f in sorted(os.listdir(subdir))]

        # Check for duplicates.
        dup_file_list = find_duplicates(file_list)

        if dup_file_list:
            print(f'Duplicate files present in sub-directory {os.path.basename(subdir)}.')
            for dup_files in dup_file_list:
                print(f"\t{', '.join([os.path.basename(f) for f in dup_files])}")
            return False

        # Check if all files are supported image formats or not.
        img_files, bad_files = check_files(file_list)

        if bad_files:
            print(f'Found {len(bad_files)} bad files in sub-directory {os.path.basename(subdir)}.')
            for bad_file in bad_files:
                print(f'\t{os.path.basename(bad_file[0])}: {bad_file[1]}')
            return False

        max_imgs = max(max_imgs, len(img_files))

    # Move images from sub-directories to parent directory and remove sub-directory.
    for subdir in subdirs:
        files = [os.path.join(subdir, f) for f in sorted(os.listdir(subdir))]
        for idx, file_ in enumerate(files):
            format_str = '{} {:0' + str(max(2, len(str(max_imgs)))) + 'd}{}'
            name = format_str.format(os.path.basename(subdir), idx+1, os.path.splitext(file_)[1])
            move(file_, os.path.join(os.path.dirname(subdir), name))
        os.rmdir(subdir)

    return True


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


def make_cbz(
    dir_path,
    h_res=None,
    jpeg=False,
    png=False,
    quality=None,
    merge_dirs=False,
    no_rename=False,
    delete=False
):
    """Make a cbz from a directory.

    dir_path : str
        Path to directory.
    h_res : int, optional
        Maximum horizontal resolution. If None no resizing is done. (default=None)
    jpeg : bool, optional
        Convert images to JPEG if True. (default=False)
    png : bool, optional
        Convert images to PNG if True. (default=False)
    quality : int, optional
        JPEG quality or PNG compression. (default=None)
    merge_dirs : bool, optional
        Merge images in subdirectories if True. (default=False)
    no_rename : bool, optional
        Don't rename files if True. (default=False)
    delete : bool, optional
        Delete original files and directory if True. (default=False)
    """
    # Make sure both jpeg and png are not True.
    if jpeg and png:
        print('--jpeg and --png cannot be used together.')
        return

    # Check if quality parameter is valid.
    if quality is not None:
        if jpeg and (quality < 0 or quality > 100):
            print('Invalid quality value. Must be between 0-100 for JPEG.')
            return
        if png and (quality < 0 or quality > 9):
            print('Invalid quality/compression value. Must be between 0-9 for PNG.')
            return
    else:
        if jpeg:
            quality = 95
        if png:
            quality = 8

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

    # If merge_dirs is True, merge subfolders.
    if merge_dirs:
        success = merge_subdirs(dir_path)
        if not success:
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
        if h_res is not None:
            width, height = img_file['size']
            scale = max(get_scale(float(height)/float(width)), 1.0)  # scale >= 1.0
            new_height = round(h_res * scale)
            new_width = round(float(width)/float(height)*float(new_height))
            new_size = (new_width, new_height)
            scale_down = height > new_height
        else:
            new_size = None
            scale_down = False

        if no_rename:
            out_name = os.path.splitext(os.path.basename(img_file['path']))[0]
        else:
            out_name = out_idx_format.format(idx + 1)
        out_file = os.path.join(dir_path, 'tmp', out_name)

        process_image(img_file, out_file, jpeg, png, quality, scale_down, new_size)

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
    parser.add_argument('-r', '--resolution', help='Maximum horizontal resolution', type=int, default=None)
    parser.add_argument('-j', '--jpeg', help='Convert all image files to JPEG', action='store_true')
    parser.add_argument('-p', '--png', help='Convert all image files to PNG', action='store_true')
    parser.add_argument(
        '-q', '--quality',
        help='Quality parameter for JPEG (0-100) or compression level for PNG (0-9)',
        type=int,
        default=None
    )
    parser.add_argument('-m', '--merge_dirs', help='Merge images in subfolders', action='store_true')
    parser.add_argument('-n', '--no_rename', help="Don't rename files", action='store_true')
    parser.add_argument('-d', '--delete', help='Delete original files', action='store_true')
    args = parser.parse_args()

    # Run make_cbz for each directory.
    for dir_path in args.dir_paths:
        dir_path = os.path.normpath(dir_path)
        print(f'Processing {dir_path} ...')
        make_cbz(
            dir_path,
            args.resolution,
            args.jpeg, args.png,
            args.quality,
            args.merge_dirs,
            args.no_rename,
            args.delete
        )


if __name__ == '__main__':
    main()
