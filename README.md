# Edge Resource Management Research Study

## What's in this repo?

* [Makefile](Makefile): Entry point for building and running experiments.
* [environment.yml](environment.yml): Conda environment dependency file.
* [app](app): Wearable cognitive assistance applications packaged as python modules for stateless vision processing.
* [data](data): experimental input data including application input traces, not version controlled under git. available on cloudlet001
* [exp](exp): experiment figures and results saved as htmls.
* [infra](infra): experiment infrastructure, including container resource usage monitoring tools (cadvisor, prometheus, grafana), and a MySQL database for experiment data. All these tools are set up using containers.
* [trace-app](trace-app): android app to record video and sensor data to collect traces
* [rmexp](rmexp): main python module "Resource Management Experiment".
* [visualization](visualization): Python Jupyter interactive plotting scripts. Used to pull data out from MySQL database and plot figures.
* [writeup](writeup): Thoughts and notes.
* [mkt](mkt): Message Broker to connect multiple feeds to multiple workers (golang + zmq).

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
  * container resource usage visualization dashboard (grafana):
    http://cloudlet002.elijah.cs.cmu.edu:3000
* launch zmq broker
```bash
# Note: we only need one port now for every component: client, worker and controller
# export BROKER_TYPE="zmq-md"
# export CLIENT_BROKER_URI="tcp://128.2.210.252:9093"
# export WORKER_BROKER_URI="tcp://128.2.210.252:9093"
python -m rmexp.broker.mdbroker --broker-uri $CLIENT_BROKER_URI
```

## Dataset

Problems:
* for lego trace 2, one of the steps is too short.
* lego trace 4 has error steps in them.

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

## Trace Dataset

### Recording Video and Sensor data

Android app VideoSensorRecorder: 
Records Video, Audio, GPS, gyroscope and accelerometer data 
source: https://github.com/waiwnf/pilotguru/tree/master/mobile/android

### Trace Collected

| Apps      | # of Traces |
| --------- | :---------: |
| Lego      |      9      |
| Ikea      |      7      |
| Face      |      8      |
| Ping-pong |      11     |
| Pool      |      4      |

## TODO steps

1. setup cloudlet002 as lego server.
2. use cloudlet001 to mimic many (16, 32, 48) clients.
3. compare dummy clients with moving some part of processing pipeline to the client.
4. Trace collection: 10x(10 min) face ; 10x(5min) lego 

## Mobile Device

* essential phone:
  Followed [this](https://forum.xda-developers.com/essential-phone/how-to/guide-how-to-install-twrp-root-t3841922) and [this](https://github.com/thehappydinoa/root-PH1) to root Essential Phone.
The patch in the root.py in the second link needs to be applied to the Magisk zip file.
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

## Section 5

* mainly trying to give a little bit more resources for each application so that they don't queue up.
* have a threshold on how large the queue is. disgard those that are not longer hopeful.
* how to manage wireless and supress clientsudo cgexec -g cpuset,memory:/rmexp stress -m 4 --vm-bytes 8g

### CGroup for experiments
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

### Launch Experiments
```bash
# make sure broker is running
./harness.py run run_config/example.yml example 
# in case worker containers are not removed cleanly:
# docker rm -f $(docker ps --filter 'name=rmexp-mc-*' -a -q) 
```
TODO: 
* in harness.py update cpu_quota and num (scheduler)
* make a plot of lego, lego + pingpong, lego + pingpong + face vs util

