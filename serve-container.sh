#! /bin/bash -ex

while [[ $# -gt 1 ]]
do
key="$1"
case $key in
    -a|--app)
    APP="$2"
    shift
    ;;
    -e|--exp)
    EXP="$2"
    shift
    ;;
    -g|--cgroup)
    CGROUP="$2"
    shift
    ;;
    -i|--interactive)
    INTERACTIVE="$2"
    shift
    ;;
    *)  # unknown option
    ;;
esac
shift # past argument or value
done

declare -A core_per_worker
core_per_worker['lego']=2
core_per_worker['pingpong']=2
core_per_worker['ikea']=32
core_per_worker['face']=2
core_per_worker['pool']=4

[[ -z "${CGROUP}" ]] && echo "CGROUP cannot be empty." && exit
[[ -z "${EXP}" ]] && echo "EXP cannot be empty." && exit
[[ -z "${core_per_worker[$APP]}" ]] && echo "$APP is not a recognized app." && exit
[[ -z "${BROKER_TYPE}" ]] && echo "BROKER_TYPE environ cannot be empty" && exit
[[ -z "${WORKER_BROKER_URI}" ]] && echo "WORKER_BROKER_URI environ cannot be empty" && exit

# get basic environ setup
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${DIR}/.envrc

get_cgroup_cpu_count(){
    cpu_set=$(cat /sys/fs/cgroup/cpuset/${CGROUP}/cpuset.cpus)
    IFS=',' read -r -a cpus <<< ${cpu_set}
    echo ${#cpus[@]}
}

get_worker_num(){
    cpu_cores=$(get_cgroup_cpu_count)
    python -c "from math import ceil; print int(ceil(float(${cpu_cores}) / ${core_per_worker[$APP]}))"
}

if [[ "${INTERACTIVE}" =~ ^([yY][eE][sS]|[yY])+$ ]]
then
    # launch interactive container
    exec docker run -it --rm \
    --name=rmexp-interactive --cgroup-parent=${CGROUP} res /bin/bash
else
    num_worker=$(get_worker_num)
    [[ -z "${num_worker}" ]] && echo "# worker cannot be empty" && exit

    # launch exp
    echo "launching experiment container (rmexp)"
    exec docker run -it --rm \
    --name=rmexp-${EXP} \
    --cgroup-parent=${CGROUP} \
    res /bin/bash -i -c \
    ". .envrc && EXP=${EXP} OMP_NUM_THREADS=${core_per_worker[$APP]} python rmexp/serve.py start --num ${num_worker} --broker-type ${BROKER_TYPE} --broker-uri ${WORKER_BROKER_URI} --app ${APP}"
fi