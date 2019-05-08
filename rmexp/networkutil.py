
from __future__ import absolute_import, division, print_function

import ast
import time

import kafka
import redis
import zmq
from logzero import logger
from rmexp import config


def get_connector(broker_type, broker_uri, *args, **kwargs):
    nc = None
    if broker_type == 'REDIS':
        nc = RedisConnector(broker_uri)
        if kwargs['redis_flush']:
            nc.flushdb()
    elif broker_type == 'zmq':
        logger.debug('using zmq connector: {} {}'.format(broker_uri, kwargs))
        nc = ZmqConnector(broker_uri, **kwargs)
    elif broker_type == 'kafka':
        nc = KafkaConnector(
            broker_uri, topic=config.STREAM_TOPIC, api_version=(2, 0, 1), **kwargs)
    return nc


def setup_broker(broker_type, broker_uri, *args, **kwargs):
    broker_cls = None
    setup_kwargs = {}
    if broker_type == 'REDIS':
        broker_cls = RedisConnector
    elif broker_type == 'zmq':
        broker_cls = ZmqConnector
    elif broker_type == 'kafka':
        broker_cls = KafkaConnector
        setup_kwargs['partition'] = kwargs['num_worker']
        setup_kwargs['topic'] = config.STREAM_TOPIC
    broker_cls.setup(broker_uri, **setup_kwargs)


class RedisConnector(object):
    @classmethod
    def setup(cls, broker_uri, *args, **kwargs):
        pass

    def __init__(self, host, port, topic=None, db=0):
        super(RedisConnector, self).__init__()
        self.client = redis.Redis(host=host, port=port, db=db)
        self._topic = topic

    def get(self):
        # blocking
        item = self.client.brpop([self._topic])
        return item


class ZmqConnector(object):
    """Zmq pair connector. zmq disables Nagle's algorithm by default.

    Arguments:
        object {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    @classmethod
    def setup(cls, broker_uri, *args, **kwargs):
        pass

    def __init__(self, uri, listen=False, tagged=False, *args, **kwargs):
        """[summary]

        Arguments:
            uri {[type]} -- [description]

        Keyword Arguments:
            listen {bool} -- [description] (default: {False})
            tagged {bool} -- Whether the ZMQ frame is tagged by ZMQ Router (default: {False})
        """

        super(ZmqConnector, self).__init__()
        self._uri = uri
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.DEALER)
        self._tagged = tagged
        if listen:
            self._socket.bind(uri)
        else:
            self._socket.connect(uri)

    def get(self, timeout=None):
        # timeout=None -> blocking
        ret = self._socket.poll(timeout)
        if ret == 0:
            return None
        else:
            tag = None
            if self._tagged:
                tag, msg = self._socket.recv_multipart()
            else:
                msg = self._socket.recv()
            return (tag, msg)

    def put(self, msg):
        if isinstance(msg, list) or isinstance(msg, tuple):
            self._socket.send_multipart(msg)
        else:
            self._socket.send(msg)


class KafkaConnector(object):
    def __init__(self, uri, topic=None, listen=False, api_version=None, group_id=None):
        super(KafkaConnector, self).__init__()
        self._topic = topic
        self._uri = uri
        if listen:
            self._conn = kafka.KafkaConsumer(
                self._topic, bootstrap_servers=uri, group_id=group_id)
        else:
            logger.debug('kafka broker uri: {}, topic: {}'.format(uri, topic))
            self._conn = kafka.KafkaProducer(
                bootstrap_servers=uri, api_version=api_version)

    @classmethod
    def setup(cls, broker_uri, partition, topic=config.STREAM_TOPIC):
        """Reinitialize topics."""
        ac = kafka.KafkaAdminClient(
            bootstrap_servers=broker_uri
        )
        ktopic = kafka.admin.NewTopic(
            name=topic, num_partitions=partition, replication_factor=1)

        # remove existing ones
        deleted = False
        while not deleted:
            try:
                logger.debug('trying to delete existing topic...')
                response = ac.delete_topics([topic], timeout_ms=5000)
                deleted = True
            except kafka.errors.UnknownTopicOrPartitionError as e:
                logger.debug(
                    'Unknown topic name. No need for deleteion: {}'.format(e))
                deleted = True

        # make sure the existing topic has been deleted
        able_to_create = False
        while not able_to_create:
            try:
                logger.debug('checking delete topic has finished...')
                ac.create_topics([ktopic], validate_only=True)
                able_to_create = True
            except kafka.errors.TopicAlreadyExistsError as e:
                logger.debug('topic has not been fully deleted: {}'.format(e))
                time.sleep(1)

        # create a new topic from an empty state
        logger.debug(
            'Existing topic has been deleted. trying to create a new topic...')
        ac.create_topics([ktopic])
        logger.debug('topic ({}) created!'.format(topic))

    def put(self, msg):
        future = self._conn.send(bytes(self._topic), value=bytes(msg))
        self._conn.flush()

    def get(self):
        return next(self._conn).value

    def close(self):
        self._conn.close()


if __name__ == "__main__":
    nc = KafkaConnector(uri='128.2.211.75:9092',
                        topic='feeds', api_version=(2, 0, 1))
    for _ in range(10):
        nc.put("test")
        nc.put("\xc2Hola, mundo!")

    nc.close()
