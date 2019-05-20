from __future__ import absolute_import, division, print_function

import logging
import select
import subprocess
import importlib
import math

import fire
import logzero
import numpy as np
from logzero import logger

logzero.loglevel(logging.DEBUG)


class Profiler(object):
    def __init__(self, app, cpus, mems, relative_video_uri, trace, profile_exp_name):
        super(Profiler, self).__init__()
        self.app = app
        self.cpus = cpus
        self.mems = mems
        self.relative_video_uri = relative_video_uri
        self.trace = trace
        self.profile_exp_name = profile_exp_name
        assert(type(self.cpus) is list)
        assert(type(self.mems) is list)
        assert(self.profile_exp_name is not None)

    def _issue_cmd(self, cmd_list):
        p = subprocess.Popen(
            cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        while True:
            [readables, _, _] = select.select(
                [p.stdout, p.stderr], [], [], 1)
            for readable in readables:
                if readable == p.stdout:
                    logger.debug(readable.readline()[:-1])
                elif readable == p.stderr:
                    logger.error(readable.readline()[:-1])
            if p.poll() is not None:
                break

        logger.info('return code: {}'.format(p.returncode))

    def _get_docker_cmd(self, cpu, mem, relative_video_uri, trace, app, omp_num_threads, profile_exp_name):
        # automatically calculate number of workers
        worker_num = int(math.ceil(cpu / float(omp_num_threads)))
        logger.info("Profiling dockers are limited to cgroup profile!!")
        docker_cmd = 'docker run --rm --cgroup-parent=profile --cpus={} --memory={}g -v /home/junjuew/work/resource-management/data:/root/data:ro res /bin/bash -i -c'.format(
            cpu, mem).split()
        docker_cmd.append(
            '". .envrc; OMP_NUM_THREADS={} EXP={} python rmexp/worker.py batch-process --video-uri /root/data/{} --app {} --store-profile True --trace {} --cpu {} --memory {}"'.format(
                omp_num_threads, profile_exp_name, relative_video_uri, app, trace, cpu, mem
            ))
        return docker_cmd

    def profile(self):
        app_module = importlib.import_module(self.app)
        for cpu in self.cpus:
            for mem in self.mems:
                docker_cmd = self._get_docker_cmd(
                    cpu, mem, self.relative_video_uri,
                    self.trace, self.app, app_module.OMP_NUM_THREADS,
                    self.profile_exp_name
                )
                logger.debug('issuing:\n{}'.format(' '.join(docker_cmd)))
                self._issue_cmd(' '.join(docker_cmd))


def main(app):
    profile_exp_name = 'c001-cg-wall-w1'
    if app == 'lego':
        profiler = Profiler('lego',
                            list(np.arange(1, 5, 1)),
                            list(np.arange(2, 2.5, 0.5)),
                            'lego-trace/1/video.mp4',
                            'lego-tr1-profile',
                            profile_exp_name
                            )
        profiler.profile()
    elif app == 'pingpong':
        profiler = Profiler('pingpong',
                            list(np.arange(1, 5, 1)),
                            list(np.arange(2, 2.5, 0.5)),
                            'pingpong-trace/10/video.mp4',
                            'pingpong-tr10-profile',
                            profile_exp_name
                            )
        profiler.profile()
    elif app == 'pool':
        profiler = Profiler('pool',
                            list(np.arange(1, 5, 1)),
                            list(np.arange(2, 2.5, 0.5)),
                            'pool-trace/1/video.mp4',
                            'pool-tr1-profile',
                            profile_exp_name
                            )
        profiler.profile()
    elif app == 'face':
        profiler = Profiler('face',
                            list(np.arange(1, 5, 1)),
                            list(np.arange(2, 2.5, 0.5)),
                            'face-trace/0/video.mp4',
                            'face-tr0-profile',
                            profile_exp_name)
        profiler.profile()


if __name__ == "__main__":
    fire.Fire()
