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
from rmexp.schema import models


def interval_extract(list, slack=30):
    length = len(list)
    i = 0
    while (i < length):
        low = list[i]
        while i < length - 1 and (list[i + 1] - list[i]) < slack:
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
    """Return symbolic state dataframes in the same order as they appear in the database.
    By default, they are ordered as frame sequence.
    """
    name = '{}-tr{}'.format(app, trace_id)
    df = pd.read_sql(
        "select * from SS where name like %(name)s",
        schema.engine,
        params={'name': name}
    )
    # SS's database frame index somehow started from 1, this is to fix it
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


def upload_lego_gt_inst_idx(trace_id, detected_stages, store=False):
    """called by duty-cycle.ipynb
    """
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


def upload_ikea_gt_inst_idx(trace_id, key_fids, store=False):
    """called by ikea_stats.ipynb
    """
    app = 'ikea'
    stat = json.dumps(
        {
            'inst_idx': key_fids
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


def get_ikea_inst_idx(ss_df):
    ss_df_inst = ss_df[ss_df['val'].str.contains('Detected', regex=False)]
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
        'face': get_face_inst_idx,
        'ikea': get_ikea_inst_idx
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
    correct_idx = map(lambda x: int(x) - 1, datastat['inst_idx'])
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
    # ikea uses proc delays as well for now
    if app == 'pool' or app == 'pingpong' or app == 'ikea':
        for inst_idx in exp_inst_idx:
            proc_delay = df[df['index'] == str(inst_idx)]['reply'].mean()
            delays.append(round(proc_delay))
        return exp_inst_idx, delays
    else:
        gt_idx = np.array(get_gt_inst_idx(app, trace_id))
        for inst_idx in exp_inst_idx:
            frame_delay = inst_idx - gt_idx[gt_idx <= inst_idx][-1]
            proc_delay = df[df['index'] == str(inst_idx)]['reply'].mean()
            delays.append(round(frame_delay * 1000. / 30. + proc_delay))
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


def run_fsm_on_ss_for_inst(fsm, ss):
    """Run FSM with a sequence of CV symbolic states as inputs and get instructions.
    """
    return ss['val'].apply(fsm.add_symbolic_state_for_instruction)


def run_fsm_on_ss_for_samples_with_dynamic_rate(fsm, ss, dynamic_sampling_rate_func):
    """Simulate dynamic sampling rate.
    sample_rate_func: function of dynamic sample rate. Input should the the time after a given instruction.
    max_mute_t: maximum time this sample_rate_func is in place

    Return simulated trace, stage_frame_idx
    """
    last_inst_t = -np.inf  # timestamp of last instruction
    cur_t = 0.0  # current timestamp in (s)
    # timestamp to get next frame. => no frame is sampled when cur_t < next_frame_t
    next_frame_t = 0.0
    trace_frame_rate = 30.0  # frame rate of trace
    # time between two adjacent records in the traces
    trace_frame_interval = 1.0 / trace_frame_rate
    cur_sample_rate = dynamic_sampling_rate_func(cur_t - last_inst_t)

    sampled_ss = []
    detected_stages = []
    for fid, fss in ss.iterrows():
        # when its' time to sample
        if cur_t >= next_frame_t:
            # sample
            sampled_ss.append(fss)
            # get instruction
            inst = fsm.add_symbolic_state_for_instruction(fss['val'])
            # state transition occurred
            if inst is not None:
                cur_sample_rate = dynamic_sampling_rate_func(
                    1e-6)  # numerical approximation
                last_inst_t = cur_t
                detected_stages.append(fss['index'])
            else:
                cur_sample_rate = dynamic_sampling_rate_func(
                    cur_t - last_inst_t)
            next_frame_t = cur_t + 1.0 / cur_sample_rate
        # advance time
        cur_t += trace_frame_interval
    return pd.DataFrame(sampled_ss), detected_stages


if __name__ == "__main__":
    fire.Fire()
