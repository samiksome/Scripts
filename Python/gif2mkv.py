#!/usr/bin/env python3

"""A simple script that converts gif to mkv.

This script takes a animated gif image and converts it to H.265 video in mkv container using imagemagick, ffmpeg and
mkvmerge. The last frame is duplicated to make sure last frame delay is not dropped.
"""

import argparse
import math
import os
from shutil import rmtree
import subprocess

from PIL import Image


def extract_frames(gif_file, out_dir, bg_color):
    """Extract frames from gif using imagemagick.

    Parameters
    ----------
    gif_file : str
        Path for gif file.
    out_dir : str
        Output directory for extracted frames.
    bg_color : str
        Background color specified as hex code.
    """
    # Extract frames.
    command = [
        'magick',
        gif_file,
        '-coalesce',
        os.path.join(out_dir, '%06d.png')
    ]

    subprocess.run(command, check=True)

    # Overlay frames on background color.
    img_files = os.listdir(out_dir)
    for img_file in img_files:
        command = [
            'magick',
            os.path.join(out_dir, img_file),
            '-background', bg_color,
            '-flatten',
            os.path.join(out_dir, img_file),
        ]

        subprocess.run(command, check=True)


def get_durations(gif_file):
    """Returns the duration of each frame in the gif.

    Parameters
    ----------
    gif_file : str
        Path for gif file.

    Returns
    -------
    durations : list[int]
        Duration of each frame in milliseconds.
    """
    with Image.open(gif_file, 'r') as img:
        durations = []
        for frame in range(img.n_frames):
            img.seek(frame)
            durations.append(max(10, img.info['duration']))

    return durations


def is_constant_fps(durations):
    """Checks whether the gif has a constant fps or not.

    Parameters
    ----------
    durations : list[int]
        Duration of each frame in milliseconds.

    Returns
    -------
    bool
        Whether gif uses constant fps.
    """
    durations = set(durations)

    # If only one delay value is present then fps is constant.
    return len(durations) == 1


def constant_fps_encode(frames_dir, durations, out_file):
    """Encoding function for constant fps gif.

    Parameters
    ----------
    frames_dir : str
        Path for extracted frames.
    durations : list[int]
        Duration of each frame in milliseconds.
    out_file : str
        Output file path.
    """
    duration = durations[0]

    # Use ffmpeg to encode the image at constant fps. Pad last frame to make sure delay is not dropped.
    command = [
        'ffmpeg',
        '-r', f'1000/{duration}',
        '-start_number', '0',
        '-i', f'{frames_dir}/%06d.png',
        '-vf', (
            'scale=out_color_matrix=bt709:out_range=full,'
            'format=yuvj444p,'
            'tpad=stop=1:stop_mode=clone'
        ),
        '-c:v', 'libx265',
        '-crf', '18',
        '-x265-params', 'input-csp=i444:colormatrix=bt709',
        '-an',
        f'{out_file}'
    ]

    subprocess.run(command, check=True)


def variable_fps_encode(frames_dir, durations, out_file):
    """Encoding function for variable fps gif.

    Uses ffmpeg constant fps encode + mkvmerge to set timecodes since ffmpeg variable doesn't seem to work properly in
    all cases.

    Parameters
    ----------
    frames_dir : str
        Path for extracted frames.
    durations : list[int]
        Duration of each frame in milliseconds.
    out_file : str
        Output file path.
    """
    # Get gcd of delays to set constant fps for ffmpeg.
    ffmpeg_duration = math.gcd(*durations)

    # Encode at constant fps using ffmpeg. Pad last frame to make sure delay is not dropped.
    command = [
        'ffmpeg',
        '-r', f'1000/{ffmpeg_duration}',
        '-start_number', '0',
        '-i', f'{frames_dir}/%06d.png',
        '-vf', (
            'scale=out_color_matrix=bt709:out_range=full,'
            'format=yuvj444p,'
            'tpad=stop=1: stop_mode=clone'
        ),
        '-c:v', 'libx265',
        '-crf', '18',
        '-x265-params', 'input-csp=i444:colormatrix=bt709',
        '-an',
        os.path.join(frames_dir, os.path.basename(out_file))
    ]

    subprocess.run(command, check=True)

    # Create proper variable timestamps file.
    timestamps_txt = '# timestamp format v2\n'
    total_time = 0
    for frame_delay in durations:
        timestamps_txt += f'{total_time}\n'
        total_time += frame_delay
    timestamps_txt += f'{total_time}\n{total_time+ffmpeg_duration}\n'

    with open(os.path.join(frames_dir, 'timestamps.txt'), 'w', encoding='utf8') as file_obj:
        file_obj.write(timestamps_txt)

    # Use mkvmerge to set correct timestamps.
    command = ['mkvmerge',
               '-o', f'{out_file}',
               '--timestamps', f"0:{os.path.join(frames_dir, 'timestamps.txt')}",
               os.path.join(frames_dir, os.path.basename(out_file))]

    subprocess.run(command, check=True)


def main():
    """Main function for the script which takes gif as input and converts it to mkv."""
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('gif_file', help='gif file to convert')
    parser.add_argument('--out_file', help='output file', default=None)
    parser.add_argument('--bg_color', help='the background color as a hex code eg. #2f213d', default='#000000')
    args = parser.parse_args()

    # Create a temporary directory to store extracted images and timestamps file.
    tmp_dir = args.gif_file[:-4] + '.tmp'
    os.mkdir(tmp_dir)

    # Extract frames and get durations.
    extract_frames(args.gif_file, tmp_dir, args.bg_color)
    durations = get_durations(args.gif_file)
    print(durations)

    # If output file is not explicitly specified use best guess.
    if args.out_file is None:
        args.out_file = args.gif_file[:-4] + '.mkv'

    # Check whether fps is constant or not and use respective encode function.
    if is_constant_fps(durations):
        constant_fps_encode(tmp_dir, durations, args.out_file)
    else:
        variable_fps_encode(tmp_dir, durations, args.out_file)

    # Clean up.
    rmtree(tmp_dir)


if __name__ == '__main__':
    main()
