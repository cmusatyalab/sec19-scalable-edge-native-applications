from __future__ import absolute_import, division, print_function

import os
import time
import types
import collections
import json

import cv2
import fire
import numpy as np
import pandas as pd
from logzero import logger
from rmexp import client, schema, utils, dbutils
from rmexp.client import fsm
from rmexp.schema import models


def get_trace_frames(app, trace_id):
    df = pd.read_sql(
        "select value from DataStat where app=%(app)s and trace=%(trace_id)s",
        schema.engine,
        params={'app': app, 'trace_id': trace_id}
    )
    datastat = json.loads(df['value'].iloc[0])
    total_frs = datastat['frames']
    return total_frs


def get_ss_df(app, trace_id):
    name = '{}-tr{}'.format(app, trace_id)
    df = pd.read_sql(
        "select * from SS where name like %(name)s",
        schema.engine,
        params={'name': name}
    )
    # SS's database index somehow started from 1, this is to fix it
    df['index'] = df['index'].astype('int32') - 1
    return df


def get_gt_active_df(app, trace_id):
    df = pd.read_sql(
        "select * from DutyCycleGT where name=%(app)s and trace=%(trace_id)s",
        schema.engine,
        params={'app': app, 'trace_id': trace_id}
    )
    df['index'] = df['index'].astype('int32')
    return df


def store_to_gt_inst(app, trace_id, stat):
    sess = dbutils.get_session()
    dbutils.insert_or_update_one(
        sess,
        models.GTInst,
        {'app': app, 'trace': str(trace_id)},
        {'value': stat}
    )
    sess.commit()
    sess.close()

# Note all these index start from 1.

# called by duty-cycle.ipynb


def upload_lego_gt_inst_idx(trace_id, detected_stages, store=False):
    stage_idx = [int(stage[0]) for stage in detected_stages]
    app = 'lego'
    stat = json.dumps(
        {
            'inst_idx': stage_idx
        }
    )
    logger.info('{} trace {}: {}'.format(app, trace_id, stat))
    if store:
        store_to_gt_inst(app, trace_id, stat)


def upload_pingpong_gt_inst_idx(trace_id, store=False):
    app = 'pingpong'
    ss_df = get_ss_df(app, trace_id)
    ss_df_inst = ss_df[ss_df['val'].str.contains('inst:', regex=False)]
    inst_idx = ss_df_inst['index'].values.tolist()
    stat = json.dumps({
        'inst_idx': inst_idx
    })
    logger.info('{} trace {}: {}'.format(app, trace_id, stat))
    if store:
        store_to_gt_inst(app, trace_id, stat)


def upload_pool_gt_inst_idx(trace_id, store=False):
    app = 'pool'
    ss_df = get_ss_df(app, trace_id)
    ss_df_inst = ss_df[ss_df['val'].str.contains('speech:', regex=False)]
    inst_idx = ss_df_inst['index'].values.tolist()
    stat = json.dumps({
        'inst_idx': inst_idx
    })
    logger.info('{} trace {}: {}'.format(app, trace_id, stat))
    if store:
        store_to_gt_inst(app, trace_id, stat)


def interval_extract(list, slack=30):
    length = len(list)
    i = 0
    while (i < length):
        low = list[i]
        while i < length-1 and (list[i + 1] - list[i]) < 30:
            i += 1
        high = list[i]
        if (high - low >= 1):
            yield [low, high]
        elif (high - low == 1):
            yield [low, ]
            yield [high, ]
        else:
            yield [low, ]
        i += 1


def upload_face_gt_inst_idx(trace_id, store=False):
    app = 'face'
    labels = ['Edmund', 'Jan', 'Junjue', 'Tom', 'Wenlu', 'Zhuo']
    ss_df = get_ss_df(app, trace_id)
    inst_idx = []
    for label in labels:
        ss_df_inst = ss_df[ss_df['val'] == label]
        label_idx = ss_df_inst['index'].values.tolist()
        label_idx_intervals = list(interval_extract(label_idx, slack=30))
        label_inst_idx = [interval[0] for interval in label_idx_intervals]
        inst_idx.extend(label_inst_idx)
        logger.info('{}: {}'.format(label, label_inst_idx))
    inst_idx = sorted(inst_idx)
    stat = json.dumps({
        'inst_idx': inst_idx
    })
    logger.info('{} trace {}: {}'.format(app, trace_id, stat))
    if store:
        store_to_gt_inst(app, trace_id, stat)


def upload_gt_inst_idx(ss_df):
    apps = ['lego', 'pingpong', 'pool', 'face']
    pass


if __name__ == "__main__":
    fire.Fire()
