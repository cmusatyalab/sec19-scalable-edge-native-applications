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

exec python rmexp/feed.py start \
--video-uri 'data/traces/lego_196/%010d.jpg' \
--broker-uri ${BROKER_ADVERTISED_HOST_NAME}:${BROKER_ADVERTISED_PORT} \
--broker-type 'kafka' \
--num ${num_feed} \
--fps ${fps} 
