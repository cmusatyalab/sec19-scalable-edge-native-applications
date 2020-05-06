# Towards scalable edge-native applications

This repository contains code and experiments for the following SEC'19 paper.

Wang, J., Feng, Z., George, S., Iyengar, R., Pillai, P., & Satyanarayanan, M. (2019, November). Towards scalable edge-native applications. In Proceedings of the 4th ACM/IEEE Symposium on Edge Computing (pp. 152-165).

## What's in this repo?

* [Makefile](Makefile): Entry point for building and running experiments.
* [environment.yml](environment.yml): Conda environment dependency file.
* [app](app): Wearable cognitive assistance applications packaged as python modules for stateless vision processing.
* [data](data): experimental input data including application input traces, not version controlled under git. See below for the download link.
* [infra](infra): experiment infrastructure, including a MySQL database for experiment data. All these tools are set up using containers.
* [rmexp](rmexp): main python module "Resource Management Experiment".
  * [rmexp/broker](rmexp/broker): Python implementation of ZMQ message broker Majordomo Pattern.
  * [rmexp/alembic](rmexp/alembic): Alembic-based database migration scripts.
  * [rmexp/client](rmexp/client): Emulated mobile client devices.
  * [rmexp/proto](rmexp/proto): Protobuf definition for client and server communication.
  * [rmexp/scheduler](rmexp/scheduler): Resource allocator: cpushare are the capped allocation using docker cpushares. Greedyratio (deprecated) is a greedy implementation that does cpu limitation even when utilization is not high.
  * [rmexp/schema](rmexp/schema): Database schema definition
* [wcautils](wcautils): python module for utilities commonly used by wearable cognitive assistance.
* [visualization](visualization): Python Jupyter interactive plotting scripts. Used to pull data out from MySQL database and plot figures.
* [writeup](writeup): Thoughts and notes.
* [scripts](scripts): Scripts to launch experiments.
* [third_party](third_party): Third party libaries required: dlib, tensorflow object detection API, and trace-app
  * [third_party/trace-app](third_party/trace-app): android app to record video and sensor data to collect traces

## Experiment Data

Data used and generated from the experiments can be downloaded from [here](https://storage.cmusatyalab.org/sec2019/data.tgz) (~20GB).

## Installation

1. install [git lfs](https://git-lfs.github.com)
2. Clone this repository
```bash
git clone https://github.com/junjuew/edge-resource-management.git
```

3. Setup conda environment.
```bash
conda env create --file environment.yml
```

  * NOTE: dlib and tensorflow is installed through pip, since opencv 2.4.13 has a fixed dependency of numpy (1.11) that is conflicting with the newest dlib and tf. conda won't allow such conflict to co-exists. However, just updating numpy to 1.16.3 still seems to be working for lego, pingpong, and pool those legacy applications.

4. Setup the infrastructure services needed for reading/writing experimental results
```bash
mv .envrc.example .envrc # set service passwords
source .envrc
cd infra && docker-compose up 
```

  * Infrastructure service:
    * MySQL database: <host>:3306
    * database management dashboard: <host>:8081

## Experiment Details

To access all experiment data and reproduce the experiements. See [this document](experiements.md).
