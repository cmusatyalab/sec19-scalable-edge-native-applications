#! /usr/bin/env python

import functools
import glob
import importlib
import multiprocessing
import os
import shutil

import fire
from logzero import logger


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
        shutil.copy(file_path, os.path.join(
            dir_path, '{:010d}'.format(idx + 1) + '.' + ext))
    shutil.rmtree(bk_dir_path)


def _get_max_trace_num(dir_path):
    fs = os.listdir(dir_path)
    nums = []
    for f in fs:
        try:
            f_int = int(f)
            nums.append(f_int)
        except ValueError as e:
            pass
    assert len(nums) > 0, 'dir_path: {} does not have traces'.format(dir_path)
    return min(nums), max(nums)


def get_video_resolution(video_uri):
    """Return video resolution (height, width)
    """
    import cv2
    cam = cv2.VideoCapture(video_uri)
    _, img = cam.read()
    if img is None:
        raise ValueError(
            'Error reading file: {}'.format(video_uri))
    cam.release()
    return img.shape[:2]


def rename_default_trace(dir_path):
    import cv2
    import shutil
    trace_num_min, trace_num_max = _get_max_trace_num(dir_path)
    for i in range(trace_num_min, trace_num_max + 1):
        cur_default_trace = os.path.join(dir_path, str(i), 'video.mp4')
        if os.path.exists(cur_default_trace) and not os.path.islink(cur_default_trace):
            res = get_video_resolution(cur_default_trace)
            assert res[0] <= res[1], '{} is not a landscape video!'.format(
                cur_default_trace)
            max_wh = max(res)
            # rename
            new_path = os.path.join(dir_path, str(
                i), 'video-{}.mp4'.format(max_wh))
            logger.debug('mv {} --> {}'.format(cur_default_trace, new_path))
            shutil.move(cur_default_trace, new_path)


def _get_highest_resolution_trace_path(trace_dir_path, trace_pattern='video*mp4'):
    """Return the video path with the highest resolution.

    Highest is defined by the max of width and height.
    """
    pat = os.path.join(trace_dir_path, trace_pattern)
    trace_paths = glob.glob(pat)
    assert len(
        trace_paths) > 0, 'dir_path: {} does not have traces'.format(pat)
    # (max(width, height), trace_path)
    path_resolution_tuples = [(max(get_video_resolution(trace_path)), trace_path) for
                              trace_path in trace_paths]
    path_resolution_tuples.sort(key=lambda x: x[0], reverse=True)
    return path_resolution_tuples[0][1]


def resize_trace(input_path, output_path, width):
    import subprocess
    cmd = 'ffmpeg -y -i {} -vf scale={}:-2 -crf 18 -vsync passthrough {}'.format(
        input_path, width, output_path)
    logger.debug('issuing: {}...'.format(cmd))
    p = subprocess.Popen(cmd, shell=True)
    p.wait()
    if p.returncode != 0:
        raise ValueError(
            'Cmd Error: {} has return code {}'.format(cmd, p.returncode))


def _get_trace_dir_path(app_dataset_dir, trace_ids):
    if trace_ids is None:
        paths = [os.path.join(app_dataset_dir, trace_id)
                 for trace_id in os.listdir(app_dataset_dir)
                 if os.path.isdir(os.path.join(app_dataset_dir, trace_id))]
    else:
        paths = [os.path.join(app_dataset_dir, str(trace_id))
                 for trace_id in trace_ids if os.path.isdir(os.path.join(app_dataset_dir, str(trace_id)))]
    return paths


def correct_app_dataset_resolution(app, app_dataset_dir_path, trace_ids=None, force=False):
    """Correct default video trace resolution based on app setting.
    It will take the max resolution video it finds, scale it 
    to the desired resolution, and create a symlink.

    app: app name
    app_dataset_dir_path: trace directory of the app. Within this directory each should be directories
    for each trace e.g. 0,1,2.
    trace_ids: a list of trace directory names. The convention is to use the id (e.g. 0, 1, 2)
    as the directory name.
    """
    if trace_ids is not None:
        assert type(
            trace_ids) == list, 'trace_ids should be a list of trace directory names not {}'.format(
                type(trace_ids))

    app = importlib.import_module(app)
    trace_dir_paths = _get_trace_dir_path(app_dataset_dir_path, trace_ids)

    # resize traces in trace_dir_path
    for trace_dir_path in trace_dir_paths:
        logger.debug('working on trace directory {}...'.format(trace_dir_path))
        trace_path = _get_highest_resolution_trace_path(trace_dir_path)
        trace_file_name = os.path.basename(trace_path)
        default_trace_path = os.path.join(trace_dir_path, 'video.mp4')

        # check if existing video.mp4 satisfies the requirements
        if os.path.islink(default_trace_path):
            if force:
                os.unlink(default_trace_path)
            else:
                shape = get_video_resolution(default_trace_path)
                if max(shape) <= app.config.IMAGE_MAX_WH:
                    continue
                os.unlink(default_trace_path)

        if max(get_video_resolution(trace_path)) > app.config.IMAGE_MAX_WH:
            resized_trace_path = os.path.join(
                trace_dir_path, 'video-{}.mp4'.format(app.config.IMAGE_MAX_WH))
            resize_trace(trace_path, resized_trace_path,
                         app.config.IMAGE_MAX_WH)
            trace_file_name = 'video-{}.mp4'.format(app.config.IMAGE_MAX_WH)

        # create link
        if os.path.exists(default_trace_path):
            if not os.path.islink(default_trace_path):
                raise ValueError('{} is not a link'.format(default_trace_path))
        os.symlink(trace_file_name, default_trace_path)


def decode_to_imgs_trace_dir(dir_path, force=False,
                             video_fname='video.mp4',
                             output_image_dname='video-images'
                             ):
    """Extract a video.mp4 in a trace directory to a dir of images."""
    import subprocess
    video_fp = os.path.join(dir_path, video_fname)
    if not os.path.exists(video_fp):
        raise ValueError('{} does not exist!'.format(video_fp))

    img_dir = os.path.join(dir_path, output_image_dname)
    if os.path.exists(img_dir):
        if force:
            logger.debug(
                'WARNING: {} exists! Force removing ...'.format(img_dir))
            shutil.rmtree(img_dir)
        else:
            raise ValueError('{} exists!'.format(img_dir))
    os.mkdir(img_dir)
    # q:v 1 is needed to make extracted jpeg images look reasonable.
    # the default value is 24.8
    # https://superuser.com/questions/318845/improve-quality-of-ffmpeg-created-jpgs
    cmd = 'ffmpeg -i {} -q:v 1 -vsync passthrough -start_number 0 {}/%010d.jpg'.format(
        video_fp, img_dir)
    logger.debug('issuing: {}'.format(cmd))
    p = subprocess.Popen(cmd, shell=True)
    p.wait()
    if p.returncode != 0:
        raise ValueError(
            'Cmd Error: {} has return code {}'.format(cmd, p.returncode))


def decode_video_to_imgs_in_app_dataset(app_dataset_dir_path, trace_ids=None, force=False):
    """Extract all traces in dir_path to images."""
    if trace_ids is not None:
        assert type(
            trace_ids) == list, 'trace_ids should be a list of trace directory names not {}'.format(
                type(trace_ids))

    worker_pool = multiprocessing.Pool(10)
    trace_dir_paths = _get_trace_dir_path(app_dataset_dir_path, trace_ids)
    job = functools.partial(decode_to_imgs_trace_dir, force=force)
    worker_pool.map_async(job, trace_dir_paths)
    worker_pool.close()
    worker_pool.join()


def get_image_sequence_resolution(image_sequence_path):
    import cv2
    img_ps = glob.glob(os.path.join(image_sequence_path, '*.jpg'))
    assert len(img_ps) > 0
    im = cv2.imread(img_ps[0])
    return im.shape[:2]


def get_dataset_stats(app, dir_path, store=False):
    """Get statistics of datasets"""
    import json
    from rmexp import dbutils, schema
    from rmexp.schema import models
    import cv2
    trace_num_min, trace_num_max = _get_max_trace_num(dir_path)
    for i in range(trace_num_min, trace_num_max + 1):
        default_trace = os.path.join(dir_path, str(i), 'video-images')
        resolution = get_image_sequence_resolution(default_trace)
        frames = len(glob.glob(os.path.join(default_trace, '*.jpg')))
        length = round(frames / 30.0, 1)
        stat = json.dumps(
            {
                'resolution': resolution,
                'frames': frames,
                'length': length
            }
        )
        logger.info('{} ({}): {}'.format(app, i, stat))
        with dbutils.session_scope(dry_run=not store) as sess:
            dbutils.insert_or_update_one(
                sess,
                models.DataStat,
                {'app': app, 'trace': str(i)},
                {'value': stat}
            )


if __name__ == '__main__':
    fire.Fire()
