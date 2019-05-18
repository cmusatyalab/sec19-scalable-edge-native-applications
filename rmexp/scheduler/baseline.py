from logzero import logger

from rmexp.scheduler import best_workers, get_app_to_users

def schedule(run_config, total_cpu, total_memory):
    """called by harness.py
    
    Arguments:
        run_config {dict} -- workload specification
        total_cpu {float} -- total CPUs
        total_memory {float} -- total memory in bytes
    
    Returns:
        start_worker_calls, start_feed_calls -- [description]
    """
    logger.debug("Using baseline scheduler")

    start_feed_calls = []
    start_worker_calls = []
    
    app_to_users = get_app_to_users(run_config)
    for app, users in app_to_users.iteritems():
        # run every app without resource limit
        start_worker_calls.append({
            'args': [],
            'kwargs': {
                'app': app,
                'num': best_workers(app, total_cpu),    # in-app
                'docker_run_kwargs': {}
            }
        })

        for u in users:
            # accept everyone
            start_feed_calls.append({
                'args': [],
                'kwargs': {
                    'app': app,
                    'video_uri': u['video_uri'],
                    'tokens_cap': 2,
                    'client_id': u['id']
                }
            })

    return start_worker_calls, start_feed_calls
