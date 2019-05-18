from collections import defaultdict
import importlib
import math

def best_workers(app, cpu, memory=None):
    # solely based on cpu now
    omp_num_threads = importlib.import_module(app).OMP_NUM_THREADS
    return int(math.ceil(cpu / float(omp_num_threads)))    # round to higer integer

def get_app_to_users(run_config):
    client_count = 0
    app_to_users = defaultdict(list)

    for c in run_config['clients']:
        for _ in range(c.get('num', 1)):
            app_to_users[c['app']].append(
                {
                    'id': client_count,
                    'video_uri': c['video_uri'],
                    'weight': c.get('weight', 1.)
                }
            )
            client_count += 1

    return app_to_users