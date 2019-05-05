#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

import ast
import collections
import multiprocessing
import os
import time

import cv2
import fire
import numpy as np
from logzero import logger

from rmexp import config, worker
from rmexp import networkutil


class JobQueue(object):
    def __init__(self, connector):
        super(JobQueue, self).__init__()
        self.connector = connector

    def get(self):
        return self.connector.get()


def start_process_loop(broker_type, broker_uri, listen, tagged):
    nc = networkutil.get_connector(
        broker_type, broker_uri, listen=listen, tagged=tagged, group_id=config.WORKER_GROUP)
    jq = JobQueue(nc)
    loop = worker.lego_loop
    loop(jq)


def start(num, broker_type, broker_uri, listen=False, tagged=True):
    """[summary]

    Arguments:
        num {[type]} -- [description]
        broker_type {[type]} -- [description]
        broker_uri {[type]} -- [description]

    Keyword Arguments:
        listen {bool} -- [description] (default: {True})
        tagged {bool} -- Used to distinguish whether zmq packet are tagged or not.
    """

    networkutil.setup_broker(broker_type, broker_uri, num_worker=num)
    procs = [multiprocessing.Process(target=start_process_loop, args=(
        broker_type, broker_uri, listen, tagged)) for i in range(num)]
    map(lambda proc: proc.start(), procs)
    map(lambda proc: proc.join(), procs)


if __name__ == "__main__":
    fire.Fire()
