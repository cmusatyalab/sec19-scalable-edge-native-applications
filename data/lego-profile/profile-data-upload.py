from __future__ import absolute_import, division, print_function

import fire
import numpy as np
from logzero import logger
from rmexp import config, dbutils
from rmexp.schema import models
import glob
import os

lego_funcs = [
    '_locate_board',
    '_find_lego',
    '_correct_orientation',
    '_reconstruct_lego'
]


def get_frame_data(lines):
    val_dict = {
        'speed': [0] * len(lego_funcs),
        'data_length': [0] * len(lego_funcs)
    }
    for line in lines:
        fn, pt, ds = line.split(',')
        # process time is integer in ms
        pt = int(float(pt))
        # data size is integer in bytes
        ds = int(ds)
        fn_idx = lego_funcs.index(fn)
        assert(fn_idx > -1)
        val_dict['speed'][fn_idx] = pt
        val_dict['data_length'][fn_idx] = ds
    val_dict['speed'] = str(val_dict['speed'])
    val_dict['data_length'] = str(val_dict['data_length'])
    return val_dict


def upload_file(filepath):
    exp = os.path.split(os.path.dirname(filepath))[1]
    name = os.path.splitext(os.path.split(filepath)[1])[0]
    trace = name[-1]
    with open(filepath, 'r') as f:
        lines = f.read().split()
        frame_start_idx = [idx for (idx, line) in enumerate(
            lines) if lego_funcs[0] in line]
        frame_end_idx = frame_start_idx[1:] + [len(lines)]
        sess = dbutils.get_session()
        for fid, (start_idx, end_idx) in enumerate(zip(frame_start_idx, frame_end_idx)):
            val_dict = get_frame_data(lines[start_idx:end_idx])
            key_dict = {
                'exp': exp,
                'name': name,
                'trace': trace,
                'index': str(fid + 1),
            }
            logger.debug(key_dict)
            logger.debug(val_dict)
            dbutils.insert_or_update_one(
                sess, models.AppProfile,
                key_dict,
                val_dict
            )
        sess.commit()
        sess.close()


def upload(dirpath):
    filepaths = glob.glob(os.path.join(dirpath, '*.txt'))
    for filepath in filepaths:
        upload_file(filepath)
    sess = dbutils.get_session()
    sess.close()


if __name__ == "__main__":
    fire.Fire()
