#! /bin/bash -ex

sudo apt install -y python-opencv python-setuptools python-virtualenv
sudo apt install -y rsync curl chrony
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python get-pip.py
sudo apt install -y libzmq5 libzmq3-dev
# pip installation is too slow as compilation is needed
sudo apt install -y python-pandas
