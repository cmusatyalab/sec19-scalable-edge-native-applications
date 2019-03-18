#! /bin/bash -ex

# get basic environ setup
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# get exp configuration
echo "# of feeds:"
read num_feed
[[ -z "${num_feed}" ]] && echo "# feed cannot be empty" && exit

echo "fps:"
read fps
[[ -z "${fps}" ]] && echo "fps cannot be empty" && exit

[[ -z "${BROKER_ADVERTISED_HOST_NAME}" ]] && echo "BROKER_ADVERTISED_HOST_NAME environ cannot be empty" && exit

python rmexp/feed.py start --num ${num_feed} \
--to_host ${BROKER_ADVERTISED_HOST_NAME} --to_port ${BROKER_ADVERTISED_PORT} --fps ${fps} \
--uri 'data/traces/lego_196/%010d.jpg' &
