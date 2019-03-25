#! /bin/bash -ex

# get basic environ setup
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/.envrc

echo "# of cpus"
read num_cpu
[[ -z "${num_cpu}" ]] && echo "# cpus cannot be empty" && exit

echo "# of memory"
read num_memory
[[ -z "${num_memory}" ]] && echo "# memory cannot be empty" && exit

read -r -p "Drop into Container Bash? [y/n] " interactive
if [[ "$interactive" =~ ^([yY][eE][sS]|[yY])+$ ]]
then
    # launch interactive container
    exec docker run -it --rm --name=rmexp --cpus=${num_cpu} --memory=${num_memory} res /bin/bash
else
    # get exp configuration
    echo "# of feeds"
    read num_feed
    [[ -z "${num_feed}" ]] && echo "# feed cannot be empty" && exit

    echo "fps:"
    read fps
    [[ -z "${fps}" ]] && echo "fps cannot be empty" && exit

    echo "# of worker processes:"
    read num_worker
    [[ -z "${num_worker}" ]] && echo "# worker cannot be empty" && exit

    read -r -p "experiment prefix (default: ${EXP_PREFIX}) " prefix
    prefix=${prefix:-$EXP_PREFIX}

    exp_name="p${prefix}f${num_feed}fps${fps}w${num_worker}c${num_cpu}m${num_memory}"
    echo "experiment name (default: ${exp_name}):"
    read custom_exp_name
    exp_name="${custom_exp_name:-$exp_name}"
    echo "experiment name: ${exp_name}"

    [[ -z "${BORKER_TYPE}" ]] && echo "BROKER_TYPE environ cannot be empty" && exit
    [[ -z "${BORKER_URI}" ]] && echo "BROKER_URI environ cannot be empty" && exit

    # launch exp
    echo "launching experiment container (rmexp)"
    docker run -d --rm --name=rmexp --cpus=${num_cpu} --memory=${num_memory} res /bin/bash -l -c \
    "conda activate resource-management && source .envrc && EXP=${exp_name} OMP_NUM_THREADS=4 python rmexp/serve.py start --num ${num_worker} --broker-type ${BROKER_TYPE} --broker-uri --broker-uri ${BROKER_URI}"

    sleep 5
    docker run -d --rm --name=rmexp-monitor res /bin/bash -l -c \
    "conda activate resource-management && source .envrc && EXP=${exp_name} python rmexp/monitor.py start --broker-type ${BROKER_TYPE} --broker-uri --broker-uri ${BROKER_URI}"
fi