#! /usr/bin/env python
from __future__ import absolute_import, division, print_function

import glob
import importlib
import json
import os
import re
import shutil

import cv2
import fire
import pandas as pd
from logzero import logger
from rmexp import dbutils, schema, utils
from rmexp.schema import models

supported_apps = ['lego', 'pingpong', 'ikea', 'pool', 'face']


def _assert_trace_dir_integrity(trace_dir, relative_video_uri, imu_fname):
    """Make sure the integrity of the trace directory"""
    app_name, trace_id = _parse_trace_dir(trace_dir)
    assert app_name in supported_apps, '{} is not supported'.format(app_name)

    video_uri = os.path.join(trace_dir, relative_video_uri)
    cam = cv2.VideoCapture(video_uri)
    # check the frame numbers are the same
    imu_fpath = os.path.join(trace_dir, imu_fname)
    df = pd.read_csv(imu_fpath, index_col='frame_id')
    # assert len(
    #     df.index) == cam.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT), 'imu data has {} samples while video has {} frames'.format(
    #         len(df.index), cam.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
    cam.release()


def _parse_trace_dir(trace_dir):
    trace_dir_fpath = os.path.abspath(trace_dir).rstrip('/')
    trace_dir_fpath_parts = trace_dir_fpath.split('/')
    trace_id = int(trace_dir_fpath_parts[-1])
    app_name = trace_dir_fpath_parts[-2].replace('-trace', '')
    return app_name, trace_id


def load_trace_dir_to_db(trace_dir,
                         relative_video_uri='video-images/%010d.jpg',
                         imu_fname='imu.csv',
                         dry_run=True):
    """Load trace directory to database.
    The trace_dir should ends with a particular naming path:
    ...../<app-name>/<trace-id>/
    """
    logger.debug('loading from dir: {}, video uri: {}'.format(
        trace_dir, os.path.join(trace_dir, relative_video_uri)))
    _create_imu_csv(trace_dir)
    _assert_trace_dir_integrity(
        trace_dir, relative_video_uri=relative_video_uri, imu_fname=imu_fname)
    app_name, trace_id = _parse_trace_dir(trace_dir)
    app = importlib.import_module(app_name)
    app_handler = app.Handler()

    # get video
    video_uri = os.path.join(trace_dir, relative_video_uri)
    cam = cv2.VideoCapture(video_uri)

    # get imu data
    imu_fpath = os.path.join(trace_dir, imu_fname)
    imu_df = pd.read_csv(imu_fpath, index_col='frame_id')
    imu_df['sensor_timestamp'] = pd.to_datetime(imu_df['sensor_timestamp'])

    with dbutils.session_scope(dry_run=dry_run) as sess:
        for row in imu_df.itertuples():
            fid = row.Index
            cam.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, fid)
            _, img = cam.read()
            symbolic_state = app_handler.process(img)
            instruction = app_handler.add_symbolic_state_for_instruction(
                symbolic_state)
            keys_dict = {'name': app_name,
                         'trace': trace_id,
                         'fid': fid}
            vals_dict = {
                'symbolic_state': symbolic_state,
                'rot_x': row.rot_x,
                'rot_y': row.rot_y,
                'rot_z': row.rot_z,
                'acc_x': row.acc_x,
                'acc_y': row.acc_y,
                'acc_z': row.acc_z,
                'sensor_timestamp': row.sensor_timestamp.to_pydatetime(),
                'instruction': instruction,
                'height': img.shape[0],
                'width': img.shape[1]
            }
            logger.debug('{}: {}'.format(
                json.dumps(keys_dict), json.dumps(vals_dict, default=str)))

            dbutils.insert_or_update_one(sess,
                                         models.Trace,
                                         keys_dict,
                                         vals_dict)
    cam.release()


def _create_imu_csv(trace_dir, output_fname='imu.csv'):
    '''
    Combines video frame number with nearest sensor data
    can ref pd df as df.loc[frame_num] = {'sensor_timestamp','rot_{x,y,z}','acc_{x,y,z}'}
    '''
    path = trace_dir
    with open(os.path.join(path, 'frames.json')) as f:
        df_frames = pd.DataFrame(json.load(f)['frames'])
        df_frames.set_index('time_usec', inplace=True)
    with open(os.path.join(path, 'rotations.json')) as f:
        df_rotations = pd.DataFrame(json.load(f)['rotations'])
        df_rotations.set_index('time_usec', inplace=True)
        df_rotations.rename(columns={'x': 'rot_x',
                                     'y': 'rot_y',
                                     'z': 'rot_z'}, inplace=True)
    with open(os.path.join(path, 'accelerations.json')) as f:
        df_accelerations = pd.DataFrame(json.load(f)['accelerations'])
        df_accelerations.set_index('time_usec', inplace=True)
        df_accelerations.rename(columns={'x': 'acc_x',
                                         'y': 'acc_y',
                                         'z': 'acc_z'}, inplace=True)
    df = pd.merge_asof(left=df_frames, right=df_rotations, left_index=True,
                       right_index=True, direction='nearest')
    df = pd.merge_asof(left=df, right=df_accelerations, left_index=True,
                       right_index=True, direction='nearest')
    df.set_index('frame_id', inplace=True)
    save_csv = os.path.join(path, output_fname)
    df.to_csv(save_csv)


def create_instruction_from_symbolic_state_in_db(app, trace_id,
                                                 dry_run=True):
    """Read symbolic state from db and update the instruction field.

    This method is used to allow fsm instruction changes while 
    avoiding re-running all symbolic state extractions.
    """
    app_name = app
    df = pd.read_sql(
        "select symbolic_state, fid from Trace where name=%(app)s and trace=%(trace_id)s order by fid",
        schema.engine,
        params={'app': app_name, 'trace_id': trace_id}
    )

    app = importlib.import_module(app)
    app_handler = app.Handler()

    with dbutils.session_scope(dry_run=dry_run) as sess:
        for row in df.itertuples():
            instruction = app_handler.add_symbolic_state_for_instruction(
                row.symbolic_state)
            keys_dict = {'name': app_name,
                         'trace': trace_id,
                         'fid': row.fid}
            vals_dict = {
                'instruction': instruction,
            }
            logger.debug('update {}: {}'.format(
                json.dumps(keys_dict), json.dumps(vals_dict, default=str)))
            dbutils.insert_or_update_one(sess,
                                         models.Trace,
                                         keys_dict,
                                         vals_dict)


if __name__ == "__main__":
    fire.Fire()
