#! /bin/bash -ex
USER="android"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

rsync -avz ${DIR}/../../../resource-management /home/${USER}/
chown -R android /home/${USER}/resource-management
sudo -i -u ${USER} bash << EOF
source ~/env/bin/activate
pip install -r ~/resource-management/infra/nexus6/requirements.txt
cd ~/resource-management/app
python setup.py install
EOF