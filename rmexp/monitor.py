#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

import time

import fire
from logzero import logger
from rmexp import config, dbutils, gabriel_pb2, networkutil
from rmexp.schema import models


def start(broker_type, broker_uri):
    nc = networkutil.get_connector(
        broker_type, broker_uri, listen=True, group_id=config.MONITOR_GROUP)
    sess = dbutils.get_session()
    while True:
        msg = nc.get()
        arrival_t = time.time()
        gabriel_msg = gabriel_pb2.Message()
        gabriel_msg.ParseFromString(msg)
        record, _ = dbutils.get_or_create(sess, models.LegoLatency,
                                          name=config.EXP, index=gabriel_msg.index)
        record.capture = gabriel_msg.timestamp
        record.arrival = arrival_t
        sess.commit()
        logger.debug('{} arrives at {}'.format(gabriel_msg.index, arrival_t))


if __name__ == "__main__":
    fire.Fire()
