# Edge Resource Management Research Study

## What's in this repo?

* [Makefile](Makefile): Entry point for building and running experiments.
* [environment.yml](environment.yml): Conda environment dependency file.
* [app](app): Wearable cognitive assistance applications packaged as python modules for stateless vision processing.
* [data](data): experimental input data including application input traces, not version controlled under git. available on cloudlet001
* [exp](exp): experiment figures and results saved as htmls.
* [infra](infra): experiment infrastructure, including container resource usage monitoring tools (cadvisor, prometheus, grafana), and a MySQL database for experiment data. All these tools are set up using containers.
* [rmexp](rmexp): main python module "Resource Management Experiment".
* [visualization](visualization): Python Jupyter interactive plotting scripts. Used to pull data out from MySQL database and plot figures.
* [writeup](writeup): Thoughts and notes.



## Infrastructure

### cadvisor, prometheus, and Grafana Setup

cadvisor is metric collection tool.
prometheus is a time-series database.
grafana is a visualization tool.

## Experiment Machine and Path

* machine: cloudlet002
* main path: /home/junjuew/work/resource-management
* conda environment:
  * install miniconda
  * add the following to ~/.condarc
```
envs_dirs:
  - /home/junjuew/work/resource-management
```
  * activate conda environment with
```bash
conda activate conda-env-rmexp
```
* Infrastructure service uris
  * MySQL database: cloudlet002.elijah.cs.cmu.edu:13306
  * database UI: http://cloudlet002.elijah.cs.cmu.edu:8081
  * container resource usage monitoring (cAdvisor) UI: http://cloudlet002.elijah.cs.cmu.edu:8080
  * time-series database for storing past container resource usages (prometheus) UI: http://cloudlet002.elijah.cs.cmu.edu:9090
  * container resource usage visualization dashboard (grafana): http://cloudlet002.elijah.cs.cmu.edu:3000

## Experiment

- prefix pwifi: -30dbm
- prefix ppoorwifi: -46dbm
- lelzmqf\*: sending the string 'load' as replacement for images, as the data
  rate is really low when sending images.
- processlatency-c1-lego_0_905: used to identify process latency of different
  lego DAG elements. batch process. used taskset to fix worker.py to a single
  core. cloudlet001. 2.3Ghz
- zmqc4m2g: used to identify process latency of different
  lego DAG elements. batch process. used taskset to fix worker.py to a single
  core. cloudlet001. 2.3Ghz
- etherzmqc8m4w8: same machine localhost, 4 clients, 2 fps
- etherzmqc8m4w8f8: same machine localhost, 8 clients, 2 fps

## Turbo-boost

Turbo-boost is restricted on cloudlet001 with for the experiments
(double-checked on 04/07.). The max clock speed is 2.3 Ghz.

## Recording Video and Sensor data

https://github.com/e-lab/VideoSensors (need to edit time-stamp)

## TODO steps

1. setup cloudlet002 as lego server.
2. use cloudlet001 to mimic many (16, 32, 48) clients.
3. compare dummy clients with moving some part of processing pipeline to the client.
