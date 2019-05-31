from __future__ import absolute_import, division, print_function

import json
import os
import time
from functools import wraps

import numpy as np


def timeit(time_log):
    def wrapper(func):
        @wraps(func)
        def timed(*args, **kw):
            ts = time.time()
            result = func(*args, **kw)
            te = time.time()
            time_log[func.__name__].append(int((te - ts) * 1000))
            return result
        return timed
    return wrapper


def pretty(app):
    d = {
        'lego': 'Lego',
        'pingpong': 'Ping Pong',
        'pool': 'Pool',
        'face': 'Face'
    }

    return d[app]


data_dir = 'data'


def trace_to_video_uri(trace):
    app, idx = trace.split('-')
    idx = int(idx[2:])
    fpath = os.path.join(data_dir, '{}-trace'.format(app),
                         str(idx), 'video.mp4')
    return os.path.join(fpath)


def video_uri_to_trace(video_uri):
    idx = os.path.basename(os.path.dirname(video_uri))
    app = os.path.basename(os.path.dirname(
        os.path.dirname(video_uri))).split('-')[0]
    return '{}-tr{}'.format(app, idx)


def trace_to_app(trace):
    return trace.split('-')[0]


class NumpyCompatibleEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
