"""
Majordomo Protocol broker
A minimal implementation of http:#rfc.zeromq.org/spec:7 and spec:8

Author: Min RK <benjaminrk@gmail.com>
Based on Java example by Arkadiusz Orzechowski
Modified by Junjue Wang
"""

import enum
import logging
import sys
import time
from binascii import hexlify
import json

import fire
import logzero
import zmq
from logzero import logger

import brokerqueue
# local
import MDP
from zhelpers import dump

logzero.loglevel(logging.INFO)

class Service(object):
    """a single Service"""
    name = None  # Service name
    _requests = None  # List of client requests
    _waiting = None  # List of waiting workers

    def __init__(self, name, requests_queue=None, **kwargs):
        self.name = name
        self._requests = [] if requests_queue is None else requests_queue
        self._waiting = []

    def add_request(self, msg):
        self._requests.append(msg)

    def add_waiting_worker(self, worker, **kwargs):
        """This is called both when a worker is first initiazlied.
        And when a worker has finished processing a request.
        """
        self._waiting.append(worker)

    def get_ready_to_send(self):
        return self._requests.pop(0), self._waiting.pop(0)

    def is_ready_to_send(self):
        return self._requests and self._waiting

    def remove_worker(self, worker):
        self._waiting.remove(worker)

    def post_worker_processing(self, *args, **kwargs):
        pass


class Scaler(object):
    Event = enum.Enum('Event', 'send recv')
    Metric_throughput = 'throughput'
    Metric_latency = 'latency'
    Action = enum.Enum('Action', 'up down')

    def __init__(self, service, expected_stats, measurement_time_interval=1):
        super(Scaler, self).__init__()
        self.service = service
        self._expected_throughput = expected_stats[self.Metric_throughput]
        self._expected_latency = expected_stats[self.Metric_latency]
        # time interval over throuput is defined. by default 1s
        # throughput
        self._measurement_time_interval = float(measurement_time_interval)
        self._requests_in_time_interval = []
        self._start_time = None
        # latency
        self._sent_to_worker_ts = {}
        self._worker_proc_latency = {}
        # scaling interval
        self._last_scale_ts = time.time()
        self._min_scale_interval = 3

    def add_stats(self, action, items):
        msg, worker = items
        if action == self.Event.send:
            self._sent_to_worker_ts[worker] = time.time()
            self._count_request()
        elif action == self.Event.recv:
            proc_latency = time.time() - self._sent_to_worker_ts[worker]
            if worker in self._worker_proc_latency:
                last_proc_latency = self._worker_proc_latency[worker]
                # a averaging window approach
                proc_latency = 0.9 * last_proc_latency + 0.1 * proc_latency
            self._worker_proc_latency[worker] = proc_latency
        else:
            raise ValueError(
                "Unrecognized add_stats action: {}".format(action))

    def _count_request(self):
        ts = time.time()
        if self._start_time is None:
            self._start_time = ts
        while self._requests_in_time_interval:
            if ts - self._requests_in_time_interval[0] > self._measurement_time_interval:
                self._requests_in_time_interval.pop(0)
            else:
                break
        self._requests_in_time_interval.append(ts)

    @property
    def throughput(self):
        return len(self._requests_in_time_interval) / self._measurement_time_interval

    @property
    def throughput_time_interval(self):
        return self._measurement_time_interval

    def scale(self):
        if time.time() - self._last_scale_ts < self._min_scale_interval:
            return
        action = None
        # scale up condition
        active_worker_latencies = [
            v for (k, v) in self._worker_proc_latency.iteritems() if k in self.service._active_pool]
        avg_latency = sum(active_worker_latencies) / float(len(active_worker_latencies))
        if avg_latency > 2. * self._expected_latency:
            self.service.inc_worker()
        
        # scale down condition
        if avg_latency < 0.5 * self._expected_latency:
            self.service.dec_worker()


class AdaptiveWorkerPoolService(Service):
    """A Service that would adapt its active worker pool."""

    # define criteria to scale up and scale down
    # handle token

    def __init__(self, name, expected_stats=None, requests_queue=None):
        super(AdaptiveWorkerPoolService, self).__init__(name,
                                                        requests_queue=requests_queue)
        self._dormant_pool = set()
        self._active_pool = set()
        assert expected_stats, '{} needs non-empty expected_stats'.format(
            self.__class__.__name__)
        self._scaler = Scaler(self, expected_stats)

    def get_ready_to_send(self):
        worker = self._waiting.pop()
        msg = self._requests.pop(0)
        self._scaler.add_stats(Scaler.Event.send, (msg, worker))
        logger.debug('[{}] Current throughput: {} rps. '.format(
            self.name,
            self._scaler.throughput
        ))
        return msg, worker

    def is_ready_to_send(self):
        return self._requests and self._waiting

    def post_worker_processing(self, msg, worker):
        """Called when worker has just finished processing an item."""
        self._scaler.add_stats(Scaler.Event.recv, (msg, worker))
        # scale workers up and down approriately
        self._scaler.scale()
        logger.debug('[{}] worker {} avg latency: {}'.format(
            self.name,
            worker.identity,
            self._scaler._worker_proc_latency[worker]))

    def add_waiting_worker(self, worker, add_to_active_if_new=True):
        """This is called both when a worker is first initiazlied.
        And when a worker has finished processing a request.
        add_to_active_if_new: whether this worker should be placed in the
        active pool if this is a new worker
        """
        if (worker not in self._dormant_pool) and (worker not in self._active_pool):
            logger.info('new worker connected: {}. active? {}'.format(
                worker.identity, add_to_active_if_new))
            if add_to_active_if_new:
                self._active_pool.add(worker)
            else:
                self._dormant_pool.add(worker)

        if worker in self._active_pool:
            self._waiting.append(worker)

    # TODO(junjuew): still need to determine how to refill/drain tokens
    # when incr or dec workers
    def inc_worker(self):
        if self._dormant_pool:
            logger.info('increased 1 worker')
            self._active_pool.add(self._dormant_pool.pop())

    def dec_worker(self):
        # make sure there is at least 1 worker running
        if len(self._active_pool) > 1:
            logger.info('decreased 1 worker')
            self._dormant_pool.add(self._active_pool.pop())


class Worker(object):
    """a Worker, idle or active"""
    identity = None  # hex Identity of worker
    address = None  # Address to route to
    service = None  # Owning service, if known
    expiry = None  # expires at this point, unless heartbeat

    def __init__(self, identity, address, lifetime):
        self.identity = identity
        self.address = address
        self.expiry = time.time() + 1e-3*lifetime


class MajorDomoBroker(object):
    """
    Majordomo Protocol broker
    A minimal implementation of http:  # rfc.zeromq.org/spec:7 and spec:8
    """

    # We'd normally pull these from config data
    INTERNAL_SERVICE_PREFIX = "mmi."
    HEARTBEAT_LIVENESS = 5  # 3-5 is reasonable
    HEARTBEAT_INTERVAL = 2500  # msecs
    HEARTBEAT_EXPIRY = HEARTBEAT_INTERVAL * HEARTBEAT_LIVENESS

    # ---------------------------------------------------------------------

    ctx = None  # Our context
    socket = None  # Socket for clients & workers
    poller = None  # our Poller

    heartbeat_at = None  # When to send HEARTBEAT
    services = None  # known services
    workers = None  # known workers
    waiting = None  # idle workers

    verbose = False  # Print activity to stdout

    # ---------------------------------------------------------------------

    def __init__(self, service_type, service_expected_stats_config=None, verbose=False, service_queue_type=list):
        """Initialize broker state."""
        self.verbose = verbose
        self.service_type = service_type
        self.service_expected_stats_config = service_expected_stats_config
        self.services = {}
        self.workers = {}
        self.waiting = []
        self.heartbeat_at = time.time() + 1e-3*self.HEARTBEAT_INTERVAL
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.ROUTER)
        self.socket.linger = 0
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.service_queue_type = service_queue_type
        logger.info(
            "Broker initialized. service_type: {}, service_expected_stats_config: {}, service_queue_type: {}".format(
                service_type,
                service_expected_stats_config,
                service_queue_type
            )
        )

    # ---------------------------------------------------------------------

    def mediate(self):
        """Main broker work happens here"""
        while True:
            try:
                items = self.poller.poll(self.HEARTBEAT_INTERVAL)
            except KeyboardInterrupt:
                break  # Interrupted
            if items:
                msg = self.socket.recv_multipart()
                if self.verbose:
                    logger.info("I: received message:")
                    logger.info(dump(msg))

                sender = msg.pop(0)
                empty = msg.pop(0)
                assert empty == ''
                header = msg.pop(0)

                if (MDP.C_CLIENT == header):
                    self.process_client(sender, msg)
                elif (MDP.W_WORKER == header):
                    self.process_worker(sender, msg)
                else:
                    logger.error("E: invalid message:")
                    logger.error(dump(msg))

            self.purge_workers()
            self.send_heartbeats()

    def destroy(self):
        """Disconnect all workers, destroy context."""
        while self.workers:
            self.delete_worker(self.workers.values()[0], True)
        self.ctx.destroy(0)

    def process_client(self, sender, msg):
        """Process a request coming from a client."""
        assert len(msg) >= 2  # Service name + body
        service = msg.pop(0)
        # Set reply return address to client sender
        msg = [sender, ''] + msg
        if service.startswith(self.INTERNAL_SERVICE_PREFIX):
            self.service_internal(service, msg)
        else:
            self.dispatch(self.require_service(service), msg)

    def process_worker(self, sender, msg):
        """Process message sent to us by a worker."""
        assert len(msg) >= 1  # At least, command

        command = msg.pop(0)

        worker_ready = hexlify(sender) in self.workers

        worker = self.require_worker(sender)

        if (MDP.W_READY == command):
            assert len(msg) >= 1  # At least, a service name
            service = msg.pop(0)
            dormant = ('true' == msg.pop(0).lower())
            # Not first command in session or Reserved service name
            if (worker_ready or service.startswith(self.INTERNAL_SERVICE_PREFIX)):
                self.delete_worker(worker, True)
            else:
                # Attach worker to service and mark as idle
                worker.service = self.require_service(service)
                self.worker_waiting(worker, add_to_active_if_new=(not dormant))

        elif (MDP.W_REPLY == command):
            if (worker_ready):
                # Remove & save client return envelope and insert the
                # protocol header and service name, then rewrap envelope.
                client = msg.pop(0)
                empty = msg.pop(0)  # ?
                msg = [client, '', MDP.C_CLIENT, worker.service.name] + msg
                worker.service.post_worker_processing(msg, worker)
                self.socket.send_multipart(msg)
                if self.verbose:
                    logger.info(
                        "I: sending to client from worker {}:".format(sender))
                    logger.info(dump(msg))
                self.worker_waiting(worker)
            else:
                self.delete_worker(worker, True)

        elif (MDP.W_HEARTBEAT == command):
            if (worker_ready):
                worker.expiry = time.time() + 1e-3*self.HEARTBEAT_EXPIRY
            else:
                self.delete_worker(worker, True)

        elif (MDP.W_DISCONNECT == command):
            self.delete_worker(worker, False)
        else:
            logger.error("E: invalid message:")
            logger.error(dump(msg))

    def delete_worker(self, worker, disconnect):
        """Deletes worker from all data structures, and deletes worker."""
        assert worker is not None
        if disconnect:
            self.send_to_worker(worker, MDP.W_DISCONNECT, None, None)

        if worker.service is not None:
            worker.service.remove_worker(worker)
        self.workers.pop(worker.identity)

    def require_worker(self, address):
        """Finds the worker(creates if necessary)."""
        assert (address is not None)
        identity = hexlify(address)
        worker = self.workers.get(identity)
        if (worker is None):
            worker = Worker(identity, address, self.HEARTBEAT_EXPIRY)
            self.workers[identity] = worker
            if self.verbose:
                logger.info("I: registering new worker: %s", identity)

        return worker

    def require_service(self, name):
        """Locates the service(creates if necessary)."""
        assert (name is not None)
        service = self.services.get(name)
        if (service is None):
            if self.service_queue_type is list:
                requests_queue = []
            else:
                requests_queue = self.service_queue_type(self)
            service_expected_stats = self.service_expected_stats_config[
                name] if name in self.service_expected_stats_config else None
            service = self.service_type(
                name, expected_stats=service_expected_stats, requests_queue=requests_queue)
            self.services[name] = service

        return service

    def bind(self, endpoint):
        """Bind broker to endpoint, can call this multiple times.

        We use a single socket for both clients and workers.
        """
        self.socket.bind(endpoint)
        logger.info("I: MDP broker/0.1.1 is active at %s", endpoint)

    def service_internal(self, service, msg):
        """Handle internal service according to 8/MMI specification"""
        returncode = "501"
        if "mmi.service" == service:
            name = msg[-1]
            returncode = "200" if name in self.services else "404"
        msg[-1] = returncode

        # insert the protocol header and service name after the routing envelope ([client, ''])
        msg = msg[:2] + [MDP.C_CLIENT, service] + msg[2:]
        self.socket.send_multipart(msg)

    def send_heartbeats(self):
        """Send heartbeats to idle workers if it's time"""
        if (time.time() > self.heartbeat_at):
            for worker in self.waiting:
                self.send_to_worker(worker, MDP.W_HEARTBEAT, None, None)

            self.heartbeat_at = time.time() + 1e-3*self.HEARTBEAT_INTERVAL

    def purge_workers(self):
        """Look for & kill expired workers.

        Workers are oldest to most recent, so we stop at the first alive worker.
        """
        while self.waiting:
            w = self.waiting[0]
            if w.expiry < time.time():
                logger.info("I: deleting expired worker: %s", w.identity)
                self.delete_worker(w, False)
                self.waiting.pop(0)
            else:
                break

    def worker_waiting(self, worker, add_to_active_if_new=False):
        """This worker is now waiting for work."""
        # Queue to broker and service waiting lists
        self.waiting.append(worker)
        worker.service.add_waiting_worker(
            worker, add_to_active_if_new=add_to_active_if_new)
        worker.expiry = time.time() + 1e-3*self.HEARTBEAT_EXPIRY
        self.dispatch(worker.service, None)

    def dispatch(self, service, msg):
        """Dispatch requests to waiting workers as possible"""
        assert (service is not None)
        if msg is not None:  # Queue message if any
            service.add_request(msg)
        self.purge_workers()
        while service.is_ready_to_send():
            msg, worker = service.get_ready_to_send()
            self.waiting.remove(worker)
            self.send_to_worker(worker, MDP.W_REQUEST, None, msg)

    def send_to_worker(self, worker, command, option, msg=None):
        """Send message to worker.

        If message is provided, sends that message.
        """

        if msg is None:
            msg = []
        elif not isinstance(msg, list):
            msg = [msg]

        # Stack routing and protocol envelopes to start of message
        # and routing envelope
        if option is not None:
            msg = [option] + msg
        msg = [worker.address, '', MDP.W_WORKER, command] + msg

        if self.verbose:
            logger.info("I: sending %r to worker", command)
            logger.info(dump(msg))

        self.socket.send_multipart(msg)

def write_sample_expected_stats_config():
    service_expected_stats_config = {
        'lego': {
            Scaler.Metric_throughput: 30,
            Scaler.Metric_latency: 100
        },
        'pingpong': {
            Scaler.Metric_throughput: 30,
            Scaler.Metric_latency: 100
        },
        'face': {
            Scaler.Metric_throughput: 30,
            Scaler.Metric_latency: 100
        },
        'pool': {
            Scaler.Metric_throughput: 30,
            Scaler.Metric_latency: 100
        },
        'ikea': {
            Scaler.Metric_throughput: 30,
            Scaler.Metric_latency: 100
        }
    }
    with open('data/profile/expected-stats.json', 'w') as f:
        json.dump(service_expected_stats_config, f)

def load_stats(fpath):
    service_expected_stats_config = {}
    if fpath is not None:
        try:
            with open(fpath, 'r') as f:
                service_expected_stats_config = json.load(f)
        except IOError as e:
            logger.error(e)
            logger.error('Error loading service exptected stats')
    return service_expected_stats_config

def main(broker_uri="tcp://*:5555", verbose=False, service_type='normal', service_queue_type='list', 
    service_expected_stats_config_fpath=None):
    """create and start new broker"""
    service_expected_stats_config = load_stats(service_expected_stats_config_fpath)
    service_type_maps = {
        'normal': Service,
        'adaptive': AdaptiveWorkerPoolService
    }
    assert service_type in service_type_maps.keys(), 'service_type must be a value of {}'.format(
        service_type_maps.keys()
    )
    service_queue_maps = {
        'latency-optimized': brokerqueue.LatencyOptimizedTokenQueue,
        'list': list
    }
    service_queue_type = service_queue_type.lower()
    assert service_queue_type in service_queue_maps.keys(), 'service_queue_type must be a value of {}'.format(
        service_queue_maps.keys()
    )
    logger.info("Using queye type: {}".format(service_queue_type))

    broker = MajorDomoBroker(
        service_type=service_type_maps[service_type], 
        service_expected_stats_config=service_expected_stats_config,
        service_queue_type=service_queue_maps[service_queue_type],
        verbose=verbose, 
        )
    broker.bind(broker_uri)
    broker.mediate()


if __name__ == '__main__':
    fire.Fire(main)
