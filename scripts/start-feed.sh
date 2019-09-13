#! /bin/bash -ex

# launch feeds to emulate client streaming video feeds

# get basic environ setup
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# get exp configuration
echo "# of feeds:"
read num_feed
[[ -z "${num_feed}" ]] && echo "# feed cannot be empty" && exit

echo "fps:"
read fps
[[ -z "${fps}" ]] && echo "fps cannot be empty" && exit
[[ -z "${BROKER_TYPE}" ]] && echo "BROKER_TYPE environ cannot be empty" && exit
[[ -z "${CLIENT_BROKER_URI}" ]] && echo "BROKER_URI environ cannot be empty" && exit

exec python rmexp/feed.py start \
--video-uri 'data/traces/lego_196/%010d.jpg' \
--broker-uri ${CLIENT_BROKER_URI} \
--broker-type ${BROKER_TYPE} \
--num ${num_feed} \
--fps ${fps} 
