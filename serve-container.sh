#! /bin/bash -ex

# get basic environ setup
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/.envrc

# get exp configuration
echo "# of feeds"
read num_feed
[[ -z "${num_feed}" ]] && echo "# feed cannot be empty" && exit

echo "# of worker processes:"
read num_worker
[[ -z "${num_worker}" ]] && echo "# worker cannot be empty" && exit

echo "# of cpus"
read num_cpu
[[ -z "${num_cpu}" ]] && echo "# cpus cannot be empty" && exit

echo "# of memory"
read num_memory
[[ -z "${num_memory}" ]] && echo "# memory cannot be empty" && exit

exp_name="f${num_feed}w${num_worker}c${num_cpu}m${num_memory}"
echo "experiment name (default: ${exp_name}):"
read custom_exp_name
exp_name="${custom_exp_name:-$exp_name}"
echo "experiment name: ${exp_name}"

docker run --rm --name=rmexp --cpus=${num_cpu} --memory=${num_memory} --link feeds-queue:redis res /bin/bash -l -c \
"conda activate resource-management && source .envrc && EXP=${exp_name} python rmexp/serve.py start --num ${num_worker} --host redis --port 6379"