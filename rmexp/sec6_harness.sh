#!/bin/bash

echo "Running $1 $2 exp=$3"

(
    EXP_TYPE=$2 ./sec6_harness.py run sec6_run_config/$1.yml server --scheduler=scheduler.$2 &
    sleep 5
    EXP_TYPE=$2 ./sec6_harness.py run sec6_run_config/$1.yml client --scheduler=scheduler.$2 --exp=$3
    sleep 2
    pkill -f harness.py
    docker rm -f $(docker ps --filter 'name=rmexp-sec6-*' -a -q)
) > log/$3.log 2>&1 