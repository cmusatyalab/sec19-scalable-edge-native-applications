from __future__ import absolute_import, division, print_function

import os

STREAM_TOPIC = 'feeds'
REDIS_RESPONSE_CHAN = 'responses'
DB_URI = os.getenv('DB_URI')
EXP = os.getenv('EXP')
