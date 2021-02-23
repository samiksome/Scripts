# crop.py

A script to crop an image in an intelligent manner trying to keep the most important parts.

Given an image the script currently maximises the crop location w.r.t. image gradients. If requested the image is first resized to fit one crop dimension.

## Requirements
- `opencv-python`
- `numpy`
- `pillow`

## Usage
    crop.py [-h] [-f] [-o OUT_FILE] img_path crop_size

positional arguments:

    img_path              Image to crop
    crop_size             Crop size as WxH

optional arguments:

    -h, --help            show this help message and exit
    -f, --fit             Resize image to fit one crop dimension
    -o OUT_FILE, --out_file OUT_FILE
                            Output file

Supply the image path, the crop size and optionally the fit parameter and output file. The crop size must be specified as `WxH` (e.g. `500x500`). If the crop size is bigger than the image, an error is printed and the script terminates. The `--fit` parameter if specified resizes the image (while maintaining the aspect ratio) to fit one of the crop dimensions. If the output file is not specified the output is placed in the same directory as the image with the name `<image>_cropped.png`

## Examples

A good and a bad example

Image | Crop without fit | Crop with fit
--- | --- | ---
![](examples/crop_1.jpg) | ![](examples/crop_1_out.png) | ![](examples/crop_1_out_fit.png)
![](examples/crop_2.jpg) | ![](examples/crop_2_out.png) | ![](examples/crop_2_out_fit.png)

It works well if the actual region of interest has the most edges, otherwise it fails since it only really looks at the density of edges in the image to decide the most important region