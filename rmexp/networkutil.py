
from __future__ import absolute_import, division, print_function

import ast

import kafka
import redis


class RedisConnector(object):
    def __init__(self, host, port, topic=None, db=0):
        super(RedisConnector, self).__init__()
        self.client = redis.Redis(host=host, port=port, db=db)
        self._topic = topic

    def get(self):
        # blocking
        item = self.client.brpop([self._topic])
        return item


class ZmqConnector(object):
    def __init__(self, uri, topic=None, listen=False):
        super(ZmqConnector, self).__init__()
        self._context = zmq.Context()
        self._socket = context.socket(zmq.PAIR)
        if listen:
            self._socket.bind(uri)

    def get(self):
        # blocking
        msg = self._socket.recv()
        return msg

    def put(self, msg):
        self._socket.send(topic, msg)
        return msg


class KafkaConnector(object):
    def __init__(self, uri, topic=None, listen=False):
        super(KafkaConnector, self).__init__()
        self._topic = topic
        if listen:
            self._conn = kafka.KafkaProducer(bootstrap_servers=uri)
        else:
            self._conn = kafka.KafkaConsumer(
                self._topic, bootstrap_servers=uri)

    def put(self, msg, topic):
        self._conn.send(self._topic, value=bytes(msg))
        self._conn.flush()

    def get(self, msg):
        self._conn.poll(max_records=1)
