from __future__ import absolute_import, division, print_function

import os
import time
from functools import wraps


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


def get_trace_video_uri(trace):
    app, idx = trace.split('-')
    idx = int(idx[2:])
    fpath = os.path.join(data_dir, '{}-trace'.format(app),
                         str(idx), 'video.mp4')
    return os.path.join(fpath)
