# Edge Resource Management Research Study

## Infrastructure

### cadvisor, prometheus, and Grafana Setup

cadvisor is metric collection tool.
prometheus is a time-series database.
grafana is a visualization tool.

## To Use

```bash
python src/exp_lego.py 'data/traces/lego_196/%010d.jpg'
```

## Development setup

```bash
cd src
vim .envrc
alembic upgrade
```

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

## TODO steps

1. setup cloudlet002 as lego server.
2. use cloudlet001 to mimic many (16, 32, 48) clients.
3. compare dummy clients with moving some part of processing pipeline to the client.

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
  * https://wiki.debian.org/HowtoDebianInAndroid


