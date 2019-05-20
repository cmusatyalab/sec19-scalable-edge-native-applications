#! /usr/bin/env python

import os
import glob
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
            dir_path, '{:010d}'.format(idx+1) + '.' + ext))
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
    for i in range(trace_num_min, trace_num_max+1):
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


def _get_highest_res_trace(dir_path):
    import glob
    trace_num_min, trace_num_max = _get_max_trace_num(dir_path)
    highest_res_traces = []
    for i in range(trace_num_min, trace_num_max+1):
        pat = os.path.join(dir_path, str(i), 'video-*mp4')
        all_traces = glob.glob(pat)
        trace_ress = [max(get_video_resolution(trace)) for trace in all_traces]
        assert len(
            trace_ress) > 0, 'dir_path: {} does not have traces'.format(pat)
        highest_res_traces.append(os.path.join(
            dir_path, str(i), 'video-{}.mp4'.format(max(trace_ress))))
    return highest_res_traces


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


def correct_trace_resolution(app, dir_path, force=False):
    """Correct default video trace resolution based on app setting.
    It will take the max resolution video it finds, scale it 
    to the desired resolution, and create a symlink.

    app: app name
    dir_path: trace directory of app. each trace should be named in
    file directories 0,1,2...
    """
    import importlib
    app = importlib.import_module(app)
    candidate_traces = _get_highest_res_trace(dir_path)
    # resize traces
    for trace in candidate_traces:
        base_dir = os.path.dirname(trace)
        actual_trace = os.path.basename(trace)
        default_trace = os.path.join(base_dir, 'video.mp4')
        logger.debug('working on dir {}...'.format(base_dir))

        # check if existing video.mp4 satisfies the requirements
        if os.path.islink(default_trace):
            if force:
                os.unlink(default_trace)
            else:
                shape = get_video_resolution(default_trace)
                if max(shape) <= app.config.IMAGE_MAX_WH:
                    continue
                os.unlink(default_trace)

        if max(get_video_resolution(trace)) > app.config.IMAGE_MAX_WH:
            output_trace = os.path.join(
                base_dir, 'video-{}.mp4'.format(app.config.IMAGE_MAX_WH))
            resize_trace(trace, output_trace, app.config.IMAGE_MAX_WH)
            actual_trace = 'video-{}.mp4'.format(app.config.IMAGE_MAX_WH)

        # create link
        if os.path.exists(default_trace):
            if not os.path.islink(default_trace):
                raise ValueError('{} is not a link'.format(default_trace))
        os.symlink(actual_trace, default_trace)


def decode_to_imgs(app, dir_path, force=False):
    import importlib
    import subprocess
    app = importlib.import_module(app)
    trace_num_min, trace_num_max = _get_max_trace_num(dir_path)
    for i in range(trace_num_min, trace_num_max+1):
        video_fp = os.path.join(dir_path, str(i), 'video.mp4')
        if not os.path.islink(video_fp):
            raise ValueError('{} does not exist'.format(video_fp))

        img_dir_name = 'video-images'
        img_dir = os.path.join(dir_path, str(i), img_dir_name)
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
        cmd = 'ffmpeg -i {} -q:v 1 -vsync passthrough {}/%010d.jpg'.format(
            video_fp, img_dir)
        logger.debug('issuing: {}'.format(cmd))
        p = subprocess.Popen(cmd, shell=True)
        p.wait()
        if p.returncode != 0:
            raise ValueError(
                'Cmd Error: {} has return code {}'.format(cmd, p.returncode))


def get_dataset_stats(app, dir_path, store=False):
    """Get statistics of datasets"""
    import json
    from rmexp import dbutils, schema
    from rmexp.schema import models
    import cv2
    trace_num_min, trace_num_max = _get_max_trace_num(dir_path)
    for i in range(trace_num_min, trace_num_max+1):
        default_trace = os.path.join(dir_path, str(i), 'video.mp4')
        resolution = get_video_resolution(default_trace)
        video = cv2.VideoCapture(default_trace)
        frames = int(video.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        length = round(frames / 30.0, 1)
        stat = json.dumps(
            {
                'resolution': resolution,
                'frames': frames,
                'length': length
            }
        )
        logger.info('{} ({}): {}'.format(app, i, stat))
        if store:
            sess = dbutils.get_session()
            dbutils.insert_or_update_one(
                sess,
                models.DataStat,
                {'app': app, 'trace': str(i)},
                {'value': stat}
            )
            sess.commit()
            sess.close()


if __name__ == '__main__':
    fire.Fire()
