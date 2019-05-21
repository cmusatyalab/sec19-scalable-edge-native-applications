#/bin/bash -ex

# exp_cpus="1 0.8 0.6"

exp_cpus="8 6 4 2"

for exp_cpu in ${exp_cpus};
do
    docker_name=rmexp-${exp_name};
    exp_name=sec6-res-util-lego-c${exp_cpu}m2
    ssh -t junjuew@cloudlet002.elijah.cs.cmu.edu "/bin/bash -l -c \" \
    docker stop -t 0 ${docker_name};
    sleep 5;
    cd /home/junjuew/work/resource-management;
    source .envrc
    ./serve-container.sh -a lego -e ${exp_name} -g rmexp -n ${exp_cpu} --docker-args --cpus=${exp_cpu} --memory=2g
    \""

    sleep 10;

    for j in 1 2 3 4;
    do
        ssh -p "818$j" root@128.2.209.237 "sudo /bin/bash -l -c \" \
        cd /sdcard/resource-management;
        source .envrc
        unbuffer timeout 180 python rmexp/feed.py start_single_feed_token \
        --video-uri data/lego-trace/${j}/video-images \
        --broker-uri tcp://128.2.210.252:9094 \
        --broker-type ${BROKER_TYPE} \
        --tokens-cap 2 \
        --app lego \
        --client_type video \
        --print-only True \
        --exp ${exp_name} > data/sec6-res-util/${exp_name}.log \"" &
    done

    sleep 220;
done

docker_name=rmexp-${exp_name};
EXP=sec6-res-util-lego-c${exp_cpu}m2
ssh junjuew@cloudlet002 "/bin/bash -l -c \" \
docker stop -t 0 ${docker_name};
\""