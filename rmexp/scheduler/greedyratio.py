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

GiB = 2.**30
TARGET_FPS = 15

def schedule(run_config, total_cpu, total_memory):
    logger.debug("Using greedy ratio scheduler")
    
    app_to_users = get_app_to_users(run_config)

    app_info = defaultdict(dict)
    
    # find each app's best util/resource point
    for app, users in app_to_users.iteritems():
        info = app_info[app]
        success, best_ratio, (best_cpu, best_memory) = find_best_util_resource_ratio(AppUtil(app))
        best_memory *= GiB
        assert success
        logger.debug("{} best ratio {} @ CPU {} mem {}".format(app, best_ratio, best_cpu, best_memory))
        info['best_ratio'], info['best_cpu'], info['best_memory'] = best_ratio, best_cpu, best_memory

    avail_cpu, avail_memory = total_cpu, total_memory

    for app, info in sorted(app_info.iteritems(), key=lambda p: p[1]['best_ratio'], reverse=True):
        if avail_cpu < 1e-3 or avail_memory < 1024:
            # docker can't accept too small cpu_quota < 1ms (1000)
            avail_cpu = avail_memory = 0.
        
        num_clients = len(app_to_users[app])
        c1, m1 = info['best_cpu'], info['best_memory']
        fps_per_worker = 1000. / AppUtil(app).latency_func(c1, m1 / GiB)
        feasible_workers = int(min(math.ceil(avail_cpu / c1), math.ceil(avail_memory / m1)))     # round up
        max_needed_workers = int(math.ceil(num_clients * TARGET_FPS / float(fps_per_worker)))   # round up
        alloted_workers = min(feasible_workers, max_needed_workers)
        info['fps_per_worker'] = fps_per_worker
        info['alloted_workers'] = alloted_workers
        info['estimated_fps'] = fps_per_worker * alloted_workers
        info['alloted_cpu'] = min(c1 * alloted_workers, avail_cpu)
        info['alloted_memory'] = min(m1 * alloted_workers, avail_memory)

        avail_cpu -= info['alloted_cpu']
        avail_memory -= info['alloted_memory']
        assert avail_cpu >= 0 and avail_memory >= 0, str(app_info)

    # rectify and re-allocate cpu/memory to consume all resource while preserving ratio
    cpus = np.array(map(itemgetter('alloted_cpu'), app_info.values()))
    cpus = total_cpu * cpus / np.sum(cpus)
    mems = np.array(map(itemgetter('alloted_memory'), app_info.values()))
    mems = total_memory * mems / np.sum(mems)
    for info, c, m in zip(app_info.values(), cpus, mems):
        info['alloted_cpu'], info['alloted_memory'] = c, m

    logger.info(json.dumps(app_info, indent=2))
    
    start_feed_calls = []
    start_worker_calls = []
    for app, info in app_info.iteritems():
        if info['alloted_workers'] > 0:
            docker_run_kwargs = {
                'cpu_period': int(100000),
                'cpu_quota': int(info['alloted_cpu'] * 100000),
                'mem_limit': int(info['alloted_memory'])
            }

            start_worker_calls.append({
                'args': [],
                'kwargs': {
                    'app': app,
                    'num': info['alloted_workers'],
                    'docker_run_kwargs': docker_run_kwargs
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



def find_best_util_resource_ratio(apputil):
    # x = (cpu, memory)
    def objective_fn(x):
        c, m = x
        util = apputil.util_func(x)
        ratio =  util / (c + .1 * m)
        # print(c, m, ratio, util)
        return -ratio   # maximize ratio

    bounds = [(0.1, 4.), (0.1, 4.)]
    x0, fval, _, _ = scipy.optimize.brute(objective_fn, bounds, full_output=True)
    return True, -fval, x0



if __name__ == "__main__":
    apps = ['lego', 'pingpong', 'pool', 'face',]
    for app in apps:
        success, best_ratio, (c1, m1) = find_best_util_resource_ratio(AppUtil(app))
        logger.info("{} best ratio {} @ CPU {} mem {}".format(app, best_ratio, c1, m1))
