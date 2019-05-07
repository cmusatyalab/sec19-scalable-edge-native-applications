from __future__ import absolute_import, division, print_function

import os

STREAM_TOPIC = 'feeds'
REDIS_RESPONSE_CHAN = 'responses'
WORKER_GROUP = 'processor'
MONITOR_GROUP = 'monitor'
DB_URI = os.getenv('DB_URI', None)
EXP = os.getenv('EXP')
