#! /bin/bash -ex

# get basic environ setup
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# get exp configuration
echo "# of feeds"
read num_feed
[[ -z "${num_feed}" ]] && echo "# feed cannot be empty" && exit

python rmexp/feed.py start --num ${num_feed} \
--to_host 127.0.0.1 --to_port 6379 --fps 10 \
--uri 'data/traces/lego_196/%010d.jpg' &
