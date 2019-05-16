from __future__ import absolute_import, division, print_function

import logging
import select
import subprocess

import fire
import logzero
import numpy as np
from logzero import logger
import itertools
import scipy
import scipy.optimize
import cPickle as pickle
logzero.loglevel(logging.DEBUG)


def group(lst, n):
    """group([0,3,4,10,2,3], 2) => iterator

    Group an iterable into an n-tuples iterable. Incomplete tuples
    are discarded e.g.

    >>> list(group(range(10), 3))
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    """
    return itertools.izip(*[itertools.islice(lst, i, None, n) for i in range(n)])


class ScipySolver(object):
    def __init__(self, fair=False):
        super(ScipySolver, self).__init__()
        self.fair = fair

    def solve(self, cpu, mem, apps, weights=None):
        x0 = zip(*[app.x0 for app in apps])

        def total_util_func(x):
            assert(len(x) % 2 == 0)
            x0, x1 = x[:len(x)//2], x[len(x)//2:]
            util_funcs = [app.util_func for app in apps]
            utils = map(lambda x: x[0](*x[1:]), zip(util_funcs, x0, x1))
            utils = np.nan_to_num(utils)

            # user weights
            if weights:
                utils = utils * weights

            if self.fair:   # max min
                util_total = np.min(utils)
            else:   # total util
                util_total = sum(utils)

            print("total, utils, x: {}, {}, {}".format(
                np.round(util_total, 2), 
                np.round(utils, 2),
                np.round(x, 2)))
            return -util_total

        def cpu_con(x):
            x0 = x[:len(x)//2]
            return cpu - np.sum(x0)

        def mem_con(x):
            x1 = x[len(x)//2:]
            return mem - np.sum(x1)

        # constraints total resource
        cons = [
            {'type': 'eq', 'fun': cpu_con},
            {'type': 'eq', 'fun': mem_con},
        ]
        # bound individual var >= 0
        bounds = [(0., cpu) for _ in range(len(apps))] + [(0., mem) for _ in range(len(apps))]

        # TODO(junjuew): need to find a reasonable bound
        res = scipy.optimize.minimize(
            total_util_func, (np.array(x0[0]), np.array(x0[1])), constraints=cons, bounds=bounds, tol=1e-6)
        return res.success, -res.fun, np.around(res.x, decimals=1)


class Allocator(object):
    """Allocate CPU, Memory to applications."""

    def __init__(self, solver):
        self.solver = solver
        super(Allocator, self).__init__()

    def solve(self, cpu, mem, apps, *args, **kwargs):
        return self.solver.solve(cpu, mem, apps, *args, **kwargs)


class AppUtil(object):
    def __init__(self, app):
        self.app = app
        self.util_func = self._load_util_func()
        self.x0 = (1, 2)
        super(AppUtil, self).__init__()

    def _load_util_func(self):
        path = '/home/junjuew/work/resource-management/data/profile/auto-worker-{}.pkl'.format(self.app)
        logger.debug("Using profile {}".format(path))
        with open(path, 'rb') as f:
            util_func = pickle.load(f)
        return util_func


if __name__ == '__main__':
    allocator = Allocator(ScipySolver(fair=True))
    cpu = 4
    mem = 8
    weights = [9, 9, 9, 9]
    app_names = ['lego', 'pingpong', 'pool', 'face']
    apps = map(AppUtil, app_names)
    print(allocator.solve(cpu, mem, apps, weights=weights))
