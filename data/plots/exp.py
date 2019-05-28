from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import fire
import json
from subprocess import Popen, PIPE
from logzero import logger


def create_config_file(num, ip):
    setup = {}
    start_from_port = 13000
    port_num_per_test = 2
    for idx in range(num):
        setup[idx] = {
            'VIDEO_STREAMING_PORT': str((idx) * port_num_per_test + start_from_port),
            'RESULT_RECEIVING_PORT': str((idx) * port_num_per_test + start_from_port + 1),
            'SERVER_IP': ip
        }
    with open('config.json', 'w') as f:
        f.write(json.dumps(setup))


def launch_single_client_by_config(config):
    client_path = '/home/junjuew/work/gabriel/client/python-client/client.py'
    video_path = '/home/junjuew/work/resource-management/lego-measurement/traces/lego/%010d.jpg'
    args = ["python", client_path, '--ip', config['SERVER_IP'], '--video-input', video_path,
            '--video-port', config['VIDEO_STREAMING_PORT'],
            '--result-port', config['RESULT_RECEIVING_PORT'],
            '--legacy', 'true']
    logger.debug(' '.join(args))
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    return proc


def launch_client():
    with open('config.json', 'r') as f:
        setup = json.loads(f.read())
    procs = []
    for (idx, config) in setup.items():
        procs.append(launch_single_client_by_config(config))
    for proc in procs:
        proc.wait()

def launch_server():
    with open('config.json', 'r') as f:
        setup = json.loads(f.read())
    import docker
    client = docker.from_env()
    for (idx, config) in setup.items():
        expose_ports = [config['VIDEO_STREAMING_PORT'], config['RESULT_RECEIVING_PORT']]
        expose_port_dict = {
            "{}/tcp".format(port): ("0.0.0.0", port) for port in expose_ports
        }
        logger.debug("expose ports: {}".format(expose_port_dict))
        client.containers.run(
            "cmusatyalab/gabriel-lego",
            '/bin/bash -c "gabriel-control -l -d -n eth0 & sleep 5; gabriel-ucomm -s 127.0.0.1:8021"',
            detach=True,
            auto_remove=True,
            name='gabriel-lego-{}'.format(idx),
            ports=expose_port_dict,
        )


if __name__ == "__main__":
    fire.Fire()
