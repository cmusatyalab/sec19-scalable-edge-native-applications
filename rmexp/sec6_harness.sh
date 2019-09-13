#!/bin/bash -ex

echo "Running $1 $2 exp=$3"

(
    ./harness.py run sec6_run_config/$1.yml server --scheduler=scheduler.$2 &
    sleep 5
    ./harness.py run sec6_run_config/$1.yml client --scheduler=scheduler.$2 --exp=$3 --enable-dutycycleimu=True
    sleep 2
    pkill -f harness.py
    docker rm -f $(docker ps --filter 'name=rmexp-harness-*' -a -q)
) > log/$3.log 2>&1