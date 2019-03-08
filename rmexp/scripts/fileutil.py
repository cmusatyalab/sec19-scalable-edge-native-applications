#! /usr/bin/env python

import os
import glob
import shutil
import fire


def rename_files_in_directory_to_sequence(dir_path, ext='jpg'):
    """Rename files to be the format of 0000000000001.ext.
    This is useful for ffmpeg/avconv to merge images into videos

    Arguments:
        dir_path {[type]} -- [description]

    Keyword Arguments:
        ext {str} -- [description] (default: {'jpg'})
    """

    # bk
    bk_dir_path = os.path.abspath(dir_path).rstrip(os.sep) + '.bk'
    shutil.copytree(dir_path, bk_dir_path)
    # remove all files that is going to be removed
    remove_file_paths = sorted(glob.glob(os.path.join(dir_path, '*' + ext)))
    for file_path in remove_file_paths:
        os.remove(file_path)
    file_paths = sorted(glob.glob(os.path.join(bk_dir_path, '*.' + ext)))
    for idx, file_path in enumerate(file_paths):
        shutil.copy(file_path, os.path.join(dir_path, '{:010d}'.format(idx+1) + '.' + ext))
    shutil.rmtree(bk_dir_path)


if __name__ == '__main__':
    fire.Fire()
