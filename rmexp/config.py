from __future__ import absolute_import, division, print_function

import os

REDIS_STREAM_CHAN = 'feeds'
DB_URI = os.getenv('DB_URI')
EXP = os.getenv('EXP')
