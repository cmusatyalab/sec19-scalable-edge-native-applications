from __future__ import absolute_import, division, print_function

import logging
import select
import subprocess
import importlib

import fire
import logzero
import numpy as np
from logzero import logger

logzero.loglevel(logging.DEBUG)


class Profiler(object):
    def __init__(self, app, cpus, mems, relative_video_uri, trace, fps):
        super(Profiler, self).__init__()
        self.app = app
        self.cpus = cpus
        self.mems = mems
        self.relative_video_uri = relative_video_uri
        self.trace = trace
        self.fps = fps
        assert(type(self.cpus) is list)
        assert(type(self.mems) is list)

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

    def _get_docker_cmd(self, cpu, mem, relative_video_uri, trace, app, fps, omp_num_threads):
        docker_cmd = 'docker run --rm --cpus={} --memory={}g -v /home/junjuew/work/resource-management/data:/root/data:ro res /bin/bash -i -c'.format(
            cpu, mem).split()
        docker_cmd.append(
            '". .envrc; OMP_NUM_THREADS={} python rmexp/worker.py batch-process --video-uri /root/data/{} --app {} --fps {} --store-profile True --trace {} --cpu {} --memory {}"'.format(
                omp_num_threads, relative_video_uri, app, fps, trace, cpu, mem
            ))
        return docker_cmd

    def profile(self):
        app_module = importlib.import_module(self.app)
        for cpu in self.cpus:
            for mem in self.mems:
                docker_cmd = self._get_docker_cmd(
                    cpu, mem, self.relative_video_uri, self.trace, self.app, self.fps, app_module.OMP_NUM_THREADS)
                logger.debug('issuing:\n{}'.format(' '.join(docker_cmd)))
                self._issue_cmd(' '.join(docker_cmd))


def main(app):
    logzero.logfile("profile-{}.log".format(app))
    if app == 'lego':
        profiler = Profiler('lego',
                            list(np.arange(0.2, 1, 0.2)),
                            list(np.arange(0.5, 3, 0.5)),
                            'lego-trace/1/video.mp4',
                            'lego-tr1-profile',
                            1)
        profiler.profile()
    elif app == 'pingpong':
        profiler = Profiler('pingpong',
                            list(np.arange(1, 2, 0.2)),
                            list(np.arange(1.5, 3, 0.5)),
                            'pingpong-trace/10/video.mp4',
                            'pingpong-tr10-profile',
                            1)
        profiler.profile()
    elif app == 'pool':
        profiler = Profiler('pool',
                            list(np.arange(2, 4, 0.4)),
                            list(np.arange(1.5, 3, 0.5)),
                            'pool-trace/1/video.mp4',
                            'pool-tr1-profile',
                            1)
        profiler.profile()
    elif app == 'face':
        profiler = Profiler('face',
                            # list(np.arange(0.2, 2, 0.5)),
                            # list(np.arange(0.5, 2, 0.5)),
                            list(np.arange(2, 4, 0.5)),
                            list(np.arange(0.5, 2, 0.5)),
                            'face-trace/2/video.mp4',
                            'face-tr2-profile',
                            0.5)
        profiler.profile()


if __name__ == "__main__":
    fire.Fire()
