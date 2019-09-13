#!/bin/bash
# Launcher script for running server-only resource allocation experiments
# Data are stored at data/sec5-resource-allocation

SCRIPT='./rmexp/harness.py'
DATA_DIR='./data/sec5-resource-allocation'

# first argument is the experiment setup file basename
# second argument is either {baseline, cpushares}
# third argument is the experiment name stored in the database

echo "Running $1 $2 exp=$3"

(
    python ${SCRIPT} run ${DATA_DIR}/run_config/$1.yml server --scheduler=scheduler.$2 &
    sleep 5
    python ${SCRIPT} run ${DATA_DIR}/run_config/$1.yml client --scheduler=scheduler.$2 --exp=$3
    sleep 2
    pkill -f harness.py
    docker rm -f $(docker ps --filter 'name=rmexp-harness-*' -a -q)
) > ${DATA_DIR}/log/$3.log 2>&1