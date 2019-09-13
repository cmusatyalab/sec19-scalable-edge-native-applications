#!/bin/bash -ex

# Launcher script for entire system evaluation
# including dutycycleimu on client + server-side resource allocation
# Measured in terms of instruction latency

# Data are stored at data/sec6-instruction-latency

SCRIPT='./rmexp/harness.py'
DATA_DIR='./data/sec6-instruction-latency'

# first argument is the experiment setup file basename
# second argument is either {baseline, cpushares} controlling whether running baseline or our optimizations
# third argument is the experiment name stored in the database

echo "Running $1 $2 exp=$3"

(
    python ${SCRIPT} run ${DATA_DIR}/run_config/$1.yml server --scheduler=scheduler.$2 &
    sleep 5
    python ${SCRIPT} run ${DATA_DIR}/run_config/$1.yml client --scheduler=scheduler.$2 --exp=$3 --enable-dutycycleimu=True
    sleep 2
    pkill -f harness.py
    docker rm -f $(docker ps --filter 'name=rmexp-harness-*' -a -q)
) > log/$3.log 2>&1