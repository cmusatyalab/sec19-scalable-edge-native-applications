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

## Dataset

Dataset for 5 applications are collected and labeled: face, lego, pingpong, pool, ikea
Their data are stored in data/<app>-trace.

Traces used for experiemnts
* face: 1-8
* pool: 1-4
* pingpong: 1-10
* lego: 1-8, 16, 18
* ikea: 1, 4, 7, 11, 12

Pool and pingpong traces are restricted to the ones that we have IMU suppression prediction.
Lego and ikea traces are restricted to the videos that triggers less errors in the original applications due to the failure of CV.
  * For lego, many traces have too short of a step or wrong color detection, causing CV errors.
  * For ikea, many traces have too short of a step, providing too little chances for a detection, especially when the client sampling rate is low.

### Recording Video and Sensor data

Android app VideoSensorRecorder: 
Records Video, Audio, GPS, gyroscope and accelerometer data 
source: https://github.com/waiwnf/pilotguru/tree/master/mobile/android

## Mobile Device Setup

### Use Linux Box to Run Ubuntu on mobile device
* essential phone:
  Follow [this](https://android.gadgethacks.com/how-to/root-your-essential-ph-1-with-magisk-0187784/1) to root Essential Phone.
* Nexus 6:
  followed [this](https://android.gadgethacks.com/how-to/magisk-101-install-magisk-root-with-twrp-0179668/):
    * first install twrp
    * then install latestest magisk manager apk as an app
    * within the app, there is "direct install" magisk disk, which successfully rooted the phone.
* Debian/Ubuntu on Android with chroot:
  * https://www.maketecheasier.com/install-ubuntu-on-android-linux-deploy/
  * install ubuntu 16.04 on linux deploy. enable sshd
* check out infra/nexus6 directory and Makefile
* update infra/nexus6/requirements.txt
* make sure feed.py can run
* rsync 
```bash
rsync -av --delete junjuew@cloudlet002.elijah.cs.cmu.edu:/home/junjuew/work/resource-management \
--exclude resource-management/conda-env-rmexp --exclude resource-management/.git --exclude resource-management/data \
--exclude resource-management/third_party --exclude resource-management/visualization \
.
```

## Application Specifics

### Pingpong
  * The workflow of pingpong is the following.
    * find_table: 'Cannot find table.'
      * when has_marked_frame:
        * find_pingpong: 'C
      * find_pingpong
        * if no marked frame: check if pingpong is on table, initialize as a
          marked frame. Otherwise, exit
        * if has marked frame: determine where the ball is hit
          * find opponent
            * if not found, exit
            * try to give instructions

#### Pingpong's Instruction
  * Category: pingpong table cannot be found:
```python
      rtn_msg = {'status': 'fail', 'message' : 'Cannot find table'}
      rtn_msg = {'status' : 'fail', 'message' : "Detected table too small: %f" % table_area_percentage}
      rtn_msg = {'status' : 'fail', 'message' : "Table top line too short"}
      rtn_msg = {'status' : 'fail', 'message' : "Table top line tilted too much"}
      rtn_msg = {'status' : 'fail', 'message' : "Table doesn't occupy bottom part of image"}
      rtn_msg = {'status' : 'fail', 'message' : "Angle between two side edge not right"}
      rtn_msg = {'status' : 'fail', 'message' : "Valid area too small after
      rotation"}
```
  * Category: pingpong cannot be found
```python
      rtn_msg = {'status' : 'fail', 'message' : "No good color candidate"}
      rtn_msg = {'status' : 'fail', 'message' : "Cannot initialize a location of ball"}
      rtn_msg = {'status' : 'fail', 'message' : "Lost track of ball: %d" % ball_moved_dist}
```
  * Category: opponent cannot be found
```python
    rtn_msg = {'status': 'fail', 'message' : 'No good featuresToTrack at all, probably no one in the scene'}
    rtn_msg = {'status': 'fail', 'message' : 'Motion too small, probably no one in the scene'}
```
  * Category: not playing
```python
            return 'idle'
```
  * Category: users don't need instructions
```python
    return 'No instruction. oppo on left, last played right.'
    return 'No instruction. oppo on right, last played left.'
```
  * Category: instructions
```python
    return 'inst: right'
    return 'inst: left'
```

## Section 5 Experiments

### Restrict Cloudlet/server Resources through CGroup
```bash
# create cgroup
sudo cgcreate -g cpuset,memory:/rmexp
# fix to cpu cores
sudo cgset -r cpuset.cpus=50,52,54,56 rmexp
# fix memory upper limit
sudo cgset -r memory.limit_in_bytes=8g rmexp
# launch a program restricting to cgroups, for containers, user cgroup-parent 
sudo cgexec -g cpuset,memory:/rmexp stress -m 4 --vm-bytes 8g
```
* profile cgroup on cloudlet002: core 0-31, memory 16g

### Running Experiments

* zmq msg broker:

```bash
# export BROKER_TYPE="zmq-md"
# export CLIENT_BROKER_URI="tcp://<host>:9093"
# export WORKER_BROKER_URI="tcp://<host>:9093"
python -m rmexp.broker.mdbroker --broker-uri $CLIENT_BROKER_URI
```

* scripts/run-sec5-resource-allocation-exp.sh:

```bash
# baseline
./scripts/run-sec5-resource-allocation-exp.sh face8pool8pingpong8lego8ikea8 baseline sec5-face8pool8pingpong8lego8ikea8-baseline
# scalable gabriel
./scripts/run-sec5-resource-allocation-exp.sh face8pool8pingpong8lego8ikea8 cpushares sec5-face8pool8pingpong8lego8ikea8-cpushares
```

#### Adding and invoking new schedulers
Add a module under `rmexp/scheduler`. Module must expose a function `schedule(run_config, total_cpu, total_memory)`. See `rmexp/scheduler/baseline.py` for an example.

## Section 6

### Commands to Run Section 6 Instruction Latency Experiments

```bash
# baseline
./scripts/run-sec6-instruction-latency-exp.sh face8pool8pingpong8lego8ikea8 baseline sec6-fppli8-baseline
# scalable gabriel
./scripts/run-sec6-instruction-latency-exp.sh face8pool8pingpong8lego8ikea8 cpushares sec6-fppli8-cpushares
```

### Make Sure Client is Sending the Right Resolution

* [rmexp/script/fileutils.py](rmexp/script/fileutils.py) creates a symlink to the video file with correct resolution
```bash
# use ffmpeg to resize video and create a symlink based on correct resolution
python fileutils.py correct-trace-resolution --app pool --dir-path ../../data/pool-trace
# rename a directory so that there is no video.mp4. Instead, video-<max_wh>.mp4 will be created
# based on the video resolution This is used to migrate from previous dataset format.
python fileutils.py rename-default-trace --dir-path ../../data/face-trace
```

## Database Tables

* DataStat: dataset statistics, e.g. length of a trace, resolution of a trace
* GTInst: ground truth (GT) for instructions. Stored are the frames that triggers instruction when all frames are processed.
* DutyCycleGT: ground truth (GT) for duty cycle. Frames are manually labeled to be in either active duty cycle or passive duty cycle.
* IMU: raw imu data for the dataset.
* IMUSuppression: imu suppression predictions made by trained SVMs. used by rmexp/client/emulator.py to simulate whether a frame should suppressed from transmission based on imu data.
* ResourceLatency: Contains all application profiling information. 'c001-cg-wall-w1' is the profiling set to use, which are profiled on cloudlet001 with 1 worker process and wall clock time stored in a cgroup of 32 hyper threads and 16G memory.
* ExpLatency: experiment results table for section 5 (run-sec5-resource-allocation-exp.sh) and section 6 (run-sec6-instruction-latency-exp.sh) experiment. See scripts dir for more. Camera-ready experiments used experiement name **sec5-face{}pool{}pingpong{}lego{}ikea{}-{baseline, cpushares}** and **sec6-fppli{4,6,8}-{baseline, cpushares}**.
* Sec6IntraApp: experiment of dutycycleimu on the client vs resource utilization at the cloudlet (run-sec6-dutycycleimu.sh).
* SS: symbolic state table. CV processing results of all the frames in the dataset.
* Trace: deprecated. not used.
* LegoLatency: deprecated. not used.
* Profile: deprecated. not used.

## Notes

* Ground truth labels for duty cycle experiements are contained in dutycycle.ipynb
