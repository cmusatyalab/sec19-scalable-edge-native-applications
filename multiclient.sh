#! /bin/bash -ex

while [[ $# -gt 1 ]]
do
key="$1"
case $key in
    -a|--app)
    APP="$2"
    shift
    ;;
    -n|--num)
    num_client="$2"
    shift
    ;;
    -e|--exp)
    EXP="$2"
    shift
    ;;
    *)  # unknown option
    ;;
esac
shift
done

declare -A trace_per_num
# these are the traces have results of IMU suppression
trace_per_num['lego']='1 2 3 4 6'
trace_per_num['pingpong']='6 7 8 9 10'
trace_per_num['pool']='1 2 3 4'
trace_per_num['ikea']=''
trace_per_num['face']=''

[[ -z "${EXP}" ]] && echo "EXP cannot be empty." && exit
[[ -z "${BROKER_TYPE}" ]] && echo "BROKER_TYPE environ cannot be empty" && exit
[[ -z "${CLIENT_BROKER_URI}" ]] && echo "WORKER_BROKER_URI environ cannot be empty" && exit
[[ -z "${trace_per_num[$APP]}" ]] && echo "$APP is not a recognized app." && exit

TOKEN=2

num_i="0"
while [[ ${num_i} -lt ${num_client} ]]
do
    for trace_i in ${trace_per_num[$APP]}; do
        echo $trace_i

        echo timeout 120 python rmexp/feed.py start_single_feed_token \
        --video-uri data/lego-trace/${trace_i}/video.mp4 \
        --app ${APP} \
        --broker-uri ${CLIENT_BROKER_URI} \
        --broker-type ${BROKER_TYPE} \
        --tokens-cap ${TOKEN} \
        --loop "True" \
        --random_start "True" \
        --exp ${EXP} \
        --client-id ${CLIENT_ID} \
        --client-type "device"

        num_i=$[${num_i}+1]
        [[ ${num_i} -ge ${num_client} ]] && exit || true
    done
done