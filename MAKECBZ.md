# makecbz.py

This script takes a directory as input and produces a CBZ file as output.

Given a directory with images, it first checks all images for supported formats and possible corrupted images. Once checked all images are converted to JPEG format with specified quality factor, if they are larger than specified resolution they are scaled down as well. The images are optionally renamed and packed into a zip file.

## Requirements
- `pillow`
- `tqdm`

## Usage
    makecbz.py [-h] [-r RESOLUTION] [-j] [-p] [-q QUALITY] [-n] [-d] dir_paths [dir_paths ...]

positional arguments:

    dir_paths             Directory/directories containing the images

optional arguments:

    -h, --help            show this help message and exit
    -r RESOLUTION, --resolution RESOLUTION
                          Maximum horizontal resolution
    -j, --jpeg            Convert all image files to JPEG
    -p, --png             Convert all image files to PNG
    -q QUALITY, --quality QUALITY
                          Quality parameter for JPEG (0-100) or compression level for PNG (0-9)
    -n, --no_rename       Don't rename files
    -d, --delete          Delete original files

Supply a directory or a list of directories (of images) to convert them into CBZ files. If there are non-image files, non-supported formats or corrupted images then a list of such files is printed out.

The images are scaled according to their aspect ratios and the specified `--resolution`. The standard aspect ratio is considered to be 2/3. Images with smaller aspect ratios (taller) are scaled to some multiple of `--resolution` in steps of `0.25 * --resolution`. If no resolution is specified the images are not scaled.

If `--jpeg` is speicified all images are converted to JPEG. Similarly if `--png` is specified all images are converted to PNG. If none is specified images are kept in their source format.

`--quality` specifies the JPEG compression quality or PNG compression level for `pillow`. It must be an integer between 0 and 100 for JPEG and 0-9 for PNG.

`--no-rename` if specified keeps the original file names of the images, otherwise they are renamed as `01.jpg`, `02.jpg`, `03.jpg`, ... (the numbers are padded with as many zeros as required). `--delete` if specified deletes the original image files as well as the directory.