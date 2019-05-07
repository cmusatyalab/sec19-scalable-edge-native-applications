#! /bin/bash -ex

source ~/env/bin/activate
pip install -r ~/resource-management/infra/nexus6/requirements.txt
cd ~/resource-management
make