from __future__ import absolute_import, division, print_function

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
