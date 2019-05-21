from collections import defaultdict
import copy
import json
from logzero import logger
import math
import numpy as np
from operator import itemgetter
import scipy
import scipy.optimize

from rmexp.schedule import AppUtil
from rmexp.scheduler import best_workers, get_app_to_users

# greedily allocate to app that has highest util/resource ratio
# until App's aggregate FPS > clients * TARGET_FPS

TARGET_FPS = 15.0

# CPU only
def schedule(run_config, total_cpu, total_memory):
    logger.debug("Using greedy ratio scheduler")
    total_memory = None
    
    app_to_users = get_app_to_users(run_config)

    app_info = defaultdict(dict)
    
    # find each app's best util/resource point
    for app, users in app_to_users.iteritems():
        info = app_info[app]
        au= AppUtil(app, 'c001-cg-wall-w1')
        success, best_ratio, (best_cpu,) = find_best_util_cpu_ratio(au)
        assert success
        logger.debug("{} best ratio {} @ CPU {} ".format(app, best_ratio, best_cpu))
        info['best_ratio'], info['best_cpu'] = best_ratio, best_cpu

    avail_cpu = total_cpu

    for app, info in sorted(app_info.iteritems(), key=lambda p: p[1]['best_ratio'], reverse=True):
        if avail_cpu < 0.1:
            # don't allocate too little CPUs
            avail_cpu = avail_memory = 0.
        
        au= AppUtil(app, 'c001-cg-wall-w1')
        num_clients = len(app_to_users[app])
        c1 = info['best_cpu']
        fps_per_worker = 1000. / au.latency_func(c1, 2.)
        feasible_workers = int(avail_cpu / c1) + 1     # round up
        max_needed_workers = int(num_clients * TARGET_FPS / fps_per_worker) + 1   # round up
        alloted_workers = min(feasible_workers, max_needed_workers)
        info['fps_per_worker'] = fps_per_worker
        info['alloted_workers'] = alloted_workers
        info['estimated_fps'] = fps_per_worker * alloted_workers
        info['alloted_cpu'] = min(c1 * alloted_workers, avail_cpu)

        avail_cpu -= info['alloted_cpu']
        assert avail_cpu >= 0

    # rectify and re-scale cpu to consume all resource while preserving ratio
    cpus = np.array(map(itemgetter('alloted_cpu'), app_info.values()))
    cpus = total_cpu * cpus / np.sum(cpus)
    for info, c in zip(app_info.values(), cpus):
        info['alloted_cpu'] = c

    logger.info(json.dumps(app_info, indent=2))
    
    start_feed_calls = []
    start_worker_calls = []
    for app, info in app_info.iteritems():
        if info['alloted_workers'] > 0:
            docker_run_kwargs = {
                'cpu_period': int(100000),
                'cpu_quota': int(info['alloted_cpu'] * 100000),
            }

            start_worker_calls.append({
                'args': [],
                'kwargs': {
                    'app': app,
                    'num': info['alloted_workers'],
                    'docker_run_kwargs': docker_run_kwargs,
                    # 'busy_wait': 1./info['fps_per_worker']  # XXX
                }
            })

            tokens = 1 + int(info['alloted_workers'] * 1.5)  # 1.0~2.0
            tokens_per_client = int(tokens / len(app_to_users[app]))

            for u in app_to_users[app]:
                start_feed_calls.append({
                    'args': [],
                    'kwargs': {
                        'app': app,
                        'video_uri': u['video_uri'],
                        'tokens_cap': min(tokens_per_client, tokens),
                        'client_id': u['id']
                    }
                })
                tokens -= tokens_per_client

    return start_worker_calls, start_feed_calls



def find_best_util_cpu_ratio(apputil, mem=2.):
    # x = (cpu,)
    def objective_fn(x):
        c = x
        util = apputil.util_func(c, mem)
        ratio =  util / (c)
        # print("util {} c {} ratio {}".format(util, c, ratio))
        return -ratio   # maximize ratio

    bounds = [(.5, 5.),]
    x0, fval, _, _ = scipy.optimize.brute(objective_fn, bounds, full_output=True)
    return True, -fval, x0



if __name__ == "__main__":
    apps = ['lego', 'pingpong', 'pool', 'face',]
    for app in apps:
        au = AppUtil(app, 'c001-cg-wall-w1')
        success, best_ratio, (c1,) = find_best_util_cpu_ratio(au)
        logger.info("{} best ratio {} @ CPU {} latency {}".format(app, best_ratio, c1, au.latency_func(c1, 2.)))
