#/bin/bash -ex

# exp_cpus="1 0.8 0.6"

exp_cpus="1"
for exp_cpu in ${exp_cpus};
do
    docker_name=rmexp-${EXP};
    EXP=sec6-res-util-lego-c${exp_cpu}m2
    ssh junjuew@cloudlet002 "/bin/bash -l -c \" \
    cd /home/junjuew/work/resource-management;
    conda activate conda-env-rmp;
    source .envrc
    docker stop -t 0 ${docker_name};
    sleep 5;
    ./serve-container.sh -a lego -e $EXP -g rmexp -n 1 --docker-args --cpus=${exp_cpu} --memory=2g
    \""

    ssh root@n6  "sudo /bin/bash -l -c \" \
    timeout 120 python rmexp/feed.py start_single_feed_token 1 \
    --video-uri data/lego-trace/1/video.mp4 \
    --broker-uri tcp://128.2.210.252:9094 \
    --broker-type $BROKER_TYPE \
    --tokens-cap 2 \
    --app lego \
    --client_type device \
    --print-only True \
    --exp ${EXP} | tee ${EXP}.log\""

    sleep 10;
done