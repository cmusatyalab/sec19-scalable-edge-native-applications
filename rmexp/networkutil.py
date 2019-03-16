
from __future__ import absolute_import, division, print_function

import ast

from rmexp import config

import redis


class RedisConnector(object):
    def __init__(self, host, port, db=0):
        super(RedisConnector, self).__init__()
        self.client = redis.Redis(host=host, port=port, db=db)

    def get(self):
        # blocking
        item = self.client.brpop([config.REDIS_STREAM_CHAN])
        return item


class ZmqConnector(object):
    def __init__(self, uri, listen=False):
        super(ZmqConnector, self).__init__()
        self._context = zmq.Context()
        self._socket = context.socket(zmq.PAIR)
        if listen:
            self._socket.bind(uri)

    def get(self):
        # blocking
        msg = self._socket.recv()
        return msg

    def send(self, msg):
        self._socket.send(msg)
        return msg
