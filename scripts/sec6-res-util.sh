#/bin/bash -ex

exp_cpus="8 6 4 2"
while [[ $# -gt 1 ]]
do
key="$1"
case $key in
    -a|--app)
    app="$2"
    shift
    ;;
    -d|--device)
    device_type="$2"
    shift
    ;;
    *)  # unknown option
    ;;
esac
shift # past argument or value
done

[[ -z "${app}" ]] && echo "app cannot be empty." && exit
[[ -z "${device_type}" ]] && echo "device_type cannot be empty." && exit

# lego's mapping to traces
declare -A lego_device_to_trace
lego_device_to_trace[1]=1
lego_device_to_trace[2]=3
lego_device_to_trace[3]=4
lego_device_to_trace[4]=6

# pingong is given token cap 3
declare -A pingpong_device_to_trace
pingpong_device_to_trace[1]=6
pingpong_device_to_trace[2]=7
pingpong_device_to_trace[3]=8
pingpong_device_to_trace[4]=9

declare -A pool_device_to_trace
pool_device_to_trace[1]=1
pool_device_to_trace[2]=2
pool_device_to_trace[3]=3
pool_device_to_trace[4]=4

# Ikea Traces 1,4,7,11,12
declare -A ikea_device_to_trace
ikea_device_to_trace[1]=1
ikea_device_to_trace[2]=4
ikea_device_to_trace[3]=7
ikea_device_to_trace[4]=11

# this is controlling for dutycycle-imu, whether dutyccycle should
# be on
declare -A dutycycle_sampling_on
dutycycle_sampling_on['lego']='True'
dutycycle_sampling_on['pingpong']='False'
dutycycle_sampling_on['pool']='False'
dutycycle_sampling_on['ikea']='True'

device_to_trace_var=${app}_device_to_trace
# indirect parameter expansion for associative array
declare -n device_to_trace=$device_to_trace_var 

for exp_cpu in ${exp_cpus};
do
    docker_name=rmexp-${exp_name};
    exp_name=sec6-res-util-${app}-c${exp_cpu}m2
    ssh -t junjuew@cloudlet002.elijah.cs.cmu.edu "/bin/bash -l -c \" \
    docker stop -t 0 ${docker_name};
    sleep 5;
    cd /home/junjuew/work/resource-management;
    source .envrc
    ./serve-container.sh -a ${app} -e ${exp_name} -g rmexp -n ${exp_cpu} --docker-args --cpus=${exp_cpu} --memory=2g
    \""

    sleep 10;

    for j in 1 2 3 4;
    do
        ssh -p "818$j" root@128.2.209.237 "sudo /bin/bash -l -c \" \
        cd /sdcard/resource-management;
        source .envrc;
        mkdir data/sec6-res-util/${device_type};
        unbuffer timeout 180 python rmexp/feed.py start_single_feed_token \
        --video-uri data/${app}-trace/${device_to_trace[$j]}/video-images \
        --app ${app} \
        --broker-uri tcp://128.2.210.252:9094 \
        --broker-type ${BROKER_TYPE} \
        --tokens-cap 1 \
        --dutycycle_sampling_on ${dutycycle_sampling_on[$app]}\
        --client_type ${device_type} \
        --client_id ${device_to_trace[$j]} \
        --print-only True \
        --exp ${exp_name} > data/sec6-res-util/${device_type}/${exp_name}.log \"" &
    done

    sleep 200;
done

docker_name=rmexp-${exp_name};
ssh junjuew@cloudlet002 "/bin/bash -l -c \" \
docker stop -t 0 ${docker_name};
\""

for i in 1 2 3 4;
do
rsync -av -e "ssh -p 818$i"  root@128.2.209.237:/sdcard/resource-management/data/sec6-res-util/${device_type}/ data/sec6-res-util/${device_type}/$i 
done