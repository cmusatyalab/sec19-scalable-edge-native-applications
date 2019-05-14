"""
Broker Queues for mdbroker
"""

import fire
import logging
import sys
import time
import zmq
import MDP


class LatencyOptimizedTokenQueue(object):
    """Queue aimed to minimize queueing latency.

    Only the newest item in the queue is returned.
    All the preivous items are directly NACKed to refill client token
    with out dispatching them to workers.
    """

    def __init__(self, broker):
        super(LatencyOptimizedTokenQueue, self).__init__()
        self.broker = broker
        self.requests = []
        self.return_to_client_service_type = 'NACK'

    def pop(self, *args, **kwargs):
        item = self.requests.pop()
        # send NACK to clients
        while len(self.requests) > 0:
            msg = self.requests.pop(0)
            client = msg.pop(0)
            empty = msg.pop(0)
            msg = ['']
            msg = [client, '', MDP.C_CLIENT,
                   self.return_to_client_service_type] + msg
            self.broker.socket.send_multipart(msg)
        return item

    def __bool__(self):
        return len(self.requests) > 0

    __nonzero__ = __bool__

    def __getattr__(self, name):
        attr = getattr(self.requests, name)
        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            return attr(*args, **kwargs)
        return wrapper
