
from __future__ import absolute_import, division, print_function

import ast

import kafka
import redis
from logzero import logger


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
    def __init__(self, uri, topic=None, listen=False, api_version=None):
        super(KafkaConnector, self).__init__()
        self._topic = topic
        if listen:
            self._conn = kafka.KafkaConsumer(
                self._topic, bootstrap_servers=uri)
        else:
            logger.debug('kafka broker uri: {}, topic: {}'.format(uri, topic))
            self._conn = kafka.KafkaProducer(
                bootstrap_servers=uri, api_version=api_version)

    def put(self, msg):
        future = self._conn.send(bytes(self._topic), value=bytes(msg))
        self._conn.flush()

    def get(self, msg):
        self._conn.poll(max_records=1)

    def close(self):
        self._conn.close()


if __name__ == "__main__":
    nc = KafkaConnector(uri='128.2.211.75:9092',
                        topic='feeds', api_version=(2, 0, 1))
    for _ in range(10):
        nc.put("test")
        nc.put("\xc2Hola, mundo!")

    nc.close()
