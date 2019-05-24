#!/bin/bash

echo "Running $1 $2 exp=$3"

(
    ./harness.py run run_config/$1.yml server --scheduler=scheduler.$2 &
    sleep 5
    ./harness.py run run_config/$1.yml client --scheduler=scheduler.$2 --exp=$3
    sleep 2
    pkill -f harness.py
    docker rm -f $(docker ps --filter 'name=rmexp-harness-*' -a -q)
) 2>&1 | tee log/$3.log