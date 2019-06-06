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


def interval_extract(list, slack=30):
    length = len(list)
    i = 0
    while (i < length):
        low = list[i]
        while i < length-1 and (list[i + 1] - list[i]) < slack:
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
    with dbutils.session_scope(dry_run=False) as sess:
        dbutils.insert_or_update_one(
            sess,
            models.GTInst,
            {'app': app, 'trace': str(trace_id)},
            {'value': stat}
        )

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
    inst_idx = get_pingpong_inst_idx(ss_df)
    stat = json.dumps({
        'inst_idx': inst_idx
    })
    logger.info('{} trace {}: {}'.format(app, trace_id, stat))
    if store:
        store_to_gt_inst(app, trace_id, stat)


def upload_pool_gt_inst_idx(trace_id, store=False):
    app = 'pool'
    ss_df = get_ss_df(app, trace_id)
    inst_idx = get_pool_inst_idx(ss_df)
    stat = json.dumps({
        'inst_idx': inst_idx
    })
    logger.info('{} trace {}: {}'.format(app, trace_id, stat))
    if store:
        store_to_gt_inst(app, trace_id, stat)


def upload_face_gt_inst_idx(trace_id, store=False):
    app = 'face'
    ss_df = get_ss_df(app, trace_id)
    inst_idx = get_face_inst_idx(ss_df)
    stat = json.dumps({
        'inst_idx': inst_idx
    })
    logger.info('{} trace {}: {}'.format(app, trace_id, stat))
    if store:
        store_to_gt_inst(app, trace_id, stat)


def get_lego_inst_idx(ss_df):
    ss_df_inst = ss_df[ss_df['val'].str.contains(
        '!!State Change!!', regex=False)]
    inst_idx = ss_df_inst['index'].values.tolist()
    return inst_idx


def get_pingpong_inst_idx(ss_df):
    ss_df_inst = ss_df[ss_df['val'].str.contains('inst:', regex=False)]
    inst_idx = ss_df_inst['index'].values.tolist()
    return inst_idx


def get_pool_inst_idx(ss_df):
    ss_df_inst = ss_df[ss_df['val'].str.contains('speech:', regex=False)]
    inst_idx = ss_df_inst['index'].values.tolist()
    return inst_idx


def get_face_inst_idx(ss_df):
    labels = ['Edmund', 'Jan', 'Junjue', 'Tom', 'Wenlu', 'Zhuo']
    inst_idx = []
    for label in labels:
        ss_df_inst = ss_df[ss_df['val'] == label]
        label_idx = ss_df_inst['index'].values.tolist()
        label_idx = map(int, label_idx)
        label_idx_intervals = list(interval_extract(label_idx, slack=3))
        label_inst_idx = [interval[0] for interval in label_idx_intervals]
        inst_idx.extend(label_inst_idx)
    inst_idx = sorted(inst_idx)
    return inst_idx


def get_inst_idx(app, df):
    """Get instruction indexs from df. 
    df must have a column named val that contains processed results.
    and index that represents frame ids
    """
    func_map = {
        'lego': get_lego_inst_idx,
        'pingpong': get_pingpong_inst_idx,
        'pool': get_pool_inst_idx,
        'face': get_face_inst_idx
    }
    inst_idx = func_map[app](df)
    return map(int, inst_idx)


def get_gt_inst_idx(app, trace_id):
    df = pd.read_sql(
        "select value from GTInst where app=%(app)s and trace=%(trace_id)s",
        schema.engine,
        params={'app': app, 'trace_id': trace_id}
    )
    assert len(df.index) == 1
    datastat = json.loads(df['value'].iloc[0])
    # correct the index to start from 0
    correct_idx = map(lambda x: int(x)-1, datastat['inst_idx'])
    return correct_idx


def get_exp_app_inst_for_client(exp, app, client_id):
    df = pd.read_sql(
        "select * from ExpLatency where name=%(exp)s and app=%(app)s and client=%(client_id)s",
        schema.engine,
        params={'app': app, 'client_id': client_id, 'exp': exp}
    )
    df['val'] = df['result']
    return get_inst_idx(app, df)


def get_exp_app_inst_delay_for_client(exp, app, client_id, trace_id):
    """Return the instruction delay in ms
    """
    df = pd.read_sql(
        "select * from ExpLatency where name=%(exp)s and app=%(app)s and client=%(client_id)s",
        schema.engine,
        params={'app': app, 'client_id': client_id,
                'exp': exp}
    )
    exp_inst_idx = get_exp_app_inst_for_client(exp, app, client_id)
    delays = []
    # pool, and pingpong are just proc delays
    if app == 'pool' or app == 'pingpong':
        for inst_idx in exp_inst_idx:
            proc_delay = df[df['index'] == str(inst_idx)]['reply'].mean()
            delays.append(round(proc_delay))
        return exp_inst_idx, delays
    else:
        gt_idx = np.array(get_gt_inst_idx(app, trace_id))
        for inst_idx in exp_inst_idx:
            frame_delay = inst_idx - gt_idx[gt_idx <= inst_idx][-1]
            proc_delay = df[df['index'] == str(inst_idx)]['reply'].mean()
            delays.append(round(frame_delay * 1000./30.+proc_delay))
        return exp_inst_idx, delays


def get_exp_app_inst_delay(exp, app):
    df = pd.read_sql(
        "select client, val from ExpLatency where name=%(exp)s and app=%(app)s group by client, val",
        schema.engine,
        params={'app': app, 'exp': exp}
    )
    client_ids = df['client'].values.tolist()
    trace_ids = df['val'].values.tolist()
    delays = {}
    for idx, client_id in enumerate(client_ids):
        delays[client_id] = get_exp_app_inst_delay_for_client(
            exp,
            app,
            client_id,
            trace_ids[idx]
        )
    return delays


if __name__ == "__main__":
    fire.Fire()
