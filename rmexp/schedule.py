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
logzero.loglevel(logging.INFO)


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

    def solve(self, cpu, mem, apps, max_clients):
        x0 = zip(*[app.x0 for app in apps])

        # objective funcation
        def total_util_func(x):
            assert(len(x) % 3 == 0)

            cpus = x[:len(apps)]
            mems = x[len(apps): 2*len(apps)]
            ks_raw = x[2*len(apps):]
            ks = np.floor(ks_raw)

            util_funcs = [app.util_func for app in apps]

            def _get_app_util((util_func, cpu, mem, k)):
                # print(util_func, cpu, mem, k)
                return k * util_func(cpu, mem)
            utils = map(_get_app_util, zip(util_funcs, cpus, mems, ks))

            if self.fair:   # max min
                util_total = np.min(utils)
            else:   # total util
                util_total = sum(utils)

            logger.debug("total: {}, utils: {}, x: {}".format(
                np.around(util_total, 1),
                np.around(utils, 1),
                np.around(x, 1)))
            return -util_total

        def cpu_con(x):
            cpus = x[:len(apps)]
            return cpu - np.sum(cpus)

        def mem_con(x):
            mems = x[len(apps): 2*len(apps)]
            return mem - np.sum(mems)

        def kworker_con(x):
            cpus = x[:len(apps)]
            mems = x[len(apps): 2*len(apps)]
            ks = np.floor(x[2*len(apps):])
            latency_funcs = [app.latency_func for app in apps]
            latencies = np.array(map(lambda arg: arg[0](
                arg[1], arg[2]), zip(latency_funcs, cpus, mems)))
            return np.array(max_clients) * 30. - ks * 1000. / latencies

        # constraints total resource
        cons = [
            {'type': 'eq', 'fun': cpu_con},
            {'type': 'eq', 'fun': mem_con},
            {'type': 'ineq', 'fun': kworker_con},
            # ks should be larger or equal than 0
            {'type': 'ineq', 'fun': lambda x: x[2*len(apps):]},
        ]

        # feasible region
        bounds = [(0.01, cpu) for _ in apps] + [(0.01, mem)
                                                for _ in apps] + list(zip([0]*len(apps), max_clients))

        res = scipy.optimize.minimize(
            total_util_func, (np.array(x0[0]), np.array(x0[1]), np.array(max_clients)), constraints=cons, bounds=bounds, tol=1e-6)
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
        self.latency_func = self._load_latency_func()
        self.x0 = (1, 2)
        super(AppUtil, self).__init__()

    def _load_util_func(self):
        path = '/home/junjuew/work/resource-management/data/profile/fix-worker-{}.pkl'.format(
            self.app)
        logger.debug("Using profile {}".format(path))
        with open(path, 'rb') as f:
            util_func = pickle.load(f)
        return util_func

    def _load_latency_func(self):
        """Latencies are in ms"""
        path = '/home/junjuew/work/resource-management/data/profile/latency-fix-worker-{}.pkl'.format(
            self.app)
        logger.debug("Using profile {}".format(path))
        with open(path, 'rb') as f:
            util_func = pickle.load(f)
        return util_func


if __name__ == '__main__':
    # pingpong is a dominate when cpu=1 and mem=2
    # dominance: pingpong >> lego >>
    allocator = Allocator(ScipySolver(fair=False))
    for cpu in range(1, 20):
        # cpu = 1
        mem = 100
        max_clients = [1.5, 1.5, 1.5, 1.5]
        app_names = ['lego', 'pingpong', 'pool', 'face']
        apps = map(AppUtil, app_names)
        logger.info(allocator.solve(cpu, mem, apps, max_clients=max_clients))
