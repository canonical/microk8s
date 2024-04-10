#!/bin/bash

# requires jq, juju, juju-wait

set -eux
# -- machine settings
BASE=${BASE:-"ubuntu@22.04"}

# -- microk8s settings
MK8S_KW_CHANNEL=${MK8S_CHANNEL:-stable}
MK8S_CP_CHANNEL=${MK8S_CHANNEL:-latest/edge/cluster-agent-test}
MK8S_CP_CONSTRAINTS=${MK8S_CP_CONSTRAINTS:-'mem=16G cores=2 root-disk=20G'}
MK8S_KW_CONSTRAINTS=${MK8S_KW_CONSTRAINTS:-'mem=2G cores=2 root-disk=10G'}

# -- juju configuration
JUJU_CONTROLLER=${JUJU_CONTROLLER:-$(juju controllers --format json | jq '.["current-controller"]' -r)}
JUJU_MODEL=${JUJU_MODEL:-juju-scale-test}
JUJU_HTTP_PROXY=""
JUJU_NO_PROXY=""
if [[ "$JUJU_CONTROLLER" == *"vsphere"* ]]; then
    JUJU_HTTP_PROXY=http://squid.internal:3128
    JUJU_NO_PROXY=10.246.154.0/24,127.0.0.1
    MICROK8S_NO_PROXY=10.0.0.0/8,127.0.0.1
fi
DEF_CONSTRAINT=${DEF_CONSTRAINT:-'mem=2G cores=1 root-disk=10G'}


EXTRA_IMAGES=(
    docker.io/cdkbot/hostpath-provisioner:1.4.2
    docker.io/grafana/promtail:2.7.2
    docker.io/grafana/grafana:9.3.8
    docker.io/grafana/tempo-query:2.0.0
    docker.io/grafana/tempo:2.0.0
    docker.io/grafana/loki:2.6.1
    docker.io/library/nginx:latest
)

function juju::model { 
    juju $1 -m ${JUJU_CONTROLLER}:${JUJU_MODEL} "${@:2}"
}

function juju:num_units {
    echo $(juju::model status --format json | jq -r '.applications["'${1}'"].units | length' || 0)
}

function juju::wait {
    sleep 5s
    juju-wait -e ${JUJU_CONTROLLER}:${JUJU_MODEL}
}

function juju::create_model() {
    juju add-model -c ${JUJU_CONTROLLER} ${JUJU_MODEL} || true
    juju::model model-config \
        juju-http-proxy=${JUJU_HTTP_PROXY} \
        juju-https-proxy=${JUJU_HTTP_PROXY} \
        juju-no-proxy=${JUJU_NO_PROXY}
}

function docker_registry_deploy () {
    if ! docker_registry_address; then
        juju::model deploy ch:docker-registry --base=${BASE} --constraints="${DEF_CONSTRAINT}"
        juju::wait
    fi
}

function docker_registry_load_images() {
    local addr=$(docker_registry_address)
    local images=( $(curl https://raw.githubusercontent.com/canonical/microk8s/master/build-scripts/images.txt) )
    local all_images=( ${images[@]} ${EXTRA_IMAGES[@]} )
    for image in "${all_images[@]}"; do
        if [[ "${image}" == docker.io* ]]; then
            docker_registry_load_image $addr $image
        fi
    done
}

function docker_registry_address () {
    juju::model exec -u docker-registry/leader -- 'unit-get public-address'
}

function docker_registry_load_image () {
    local DOCKERHUB_IO="${1}:5000"
    local IMAGE=${2}
    juju::model run docker-registry/leader push image=${IMAGE} tag=${DOCKERHUB_IO}/${IMAGE#*/}
}

function scale_application () {
    local app="${1}"
    local scale="${2}"
    local constraints=$3
    local num_units=$(juju:num_units "${app}")
    if [[ $num_units -ge $scale ]]; then
        echo "No need to scale ${app}"
    elif [[ $num_units -eq 0 ]]; then
        juju::model deploy ch:ubuntu $app --base=${BASE} --constraints="${constraints}" -n $scale
    else
        juju::model add-unit $app -n $(($scale-$num_units))
    fi
    juju::wait
    snap_install_application $app
    setup_registry $app $(docker_registry_address)
    juju::wait
}

function setup_registry () {
    local DOCKERHUB_IO="http://${2}:5000"
    juju::model exec -a "${1}" -- "$(cat <<EOF
set -eu
if [[ "${JUJU_HTTP_PROXY}" != "" ]]; then
    echo "
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin"
HTTP_PROXY=${JUJU_HTTP_PROXY}
HTTPS_PROXY=${JUJU_HTTP_PROXY}
NO_PROXY=${MICROK8S_NO_PROXY}
http_proxy=${JUJU_HTTP_PROXY}
https_proxy=${JUJU_HTTP_PROXY}
no_proxy=${MICROK8S_NO_PROXY}
" > /etc/environment
    echo Environment is now:	
    cat /etc/environment
fi
if ! grep ${DOCKERHUB_IO} /var/snap/microk8s/current/args/certs.d/docker.io/hosts.toml; then
    echo "
server = '${DOCKERHUB_IO}'
[host.'${DOCKERHUB_IO}']
  capabilities = ['pull', 'resolve']
" > /var/snap/microk8s/current/args/certs.d/docker.io/hosts.toml
    echo docker.io registry mirror:	
    cat /var/snap/microk8s/current/args/certs.d/docker.io/hosts.toml
    reboot
fi
EOF
)"
}

function snap_install_application () {
    if [ "${1}" == "mk8s-cp" ]; then
        channel=${MK8S_CP_CHANNEL}
    elif [ "${1}" == "mk8s-kw" ]; then
        channel=${MK8S_KW_CHANNEL}
    elif
        >&2 echo "Invalid channel selected for ${1}"
        exit -1
    fi
    juju::model exec -a "${1}" -- "$(cat <<EOF
set -eu
snap install microk8s --classic --channel=$channel || true
snap refresh microk8s --classic --channel=$channel
if ! [ -f /home/ubuntu/needs_joining ]; then
  echo "First time setup"
  usermod -a -G microk8s ubuntu
  mkdir -p           /home/ubuntu/.kube
  chown -f -R ubuntu /home/ubuntu/.kube
  echo 'true' >      /home/ubuntu/needs_joining
  echo ''     >      /home/ubuntu/cluster_join
  chmod +x           /home/ubuntu/cluster_join
fi
EOF
)"
}

function snap_join_cluster () {
    juju::model exec -a "${1}" -- "$(cat <<EOF
set -eu
cat /home/ubuntu/cluster_join
if grep "true" /home/ubuntu/needs_joining; then
    /home/ubuntu/cluster_join
    echo "Sleeping for 1m" && sleep 1m
fi
/snap/microk8s/current/kubectl --kubeconfig /var/snap/microk8s/current/credentials/kubelet.config get node \$(hostname)
echo '' > /home/ubuntu/cluster_join
echo 'false' > /home/ubuntu/needs_joining
EOF
)"
}

function snap_prepare_to_join () {
    juju::model exec -a "${1}" -- "$(cat <<EOF
set -eu
if grep "true" /home/ubuntu/needs_joining; then
    echo $2 > /home/ubuntu/cluster_join
fi
EOF
)"
}

function snap_cluster_add () {
    juju::model exec -u mk8s-cp/leader -- "$(cat <<EOF
set -eu
echo 'false' > /home/ubuntu/needs_joining
microk8s add-node --token-ttl 1000000 --format short | tail -n 1
EOF
)"
}

function snap_cluster_application () {
    snap_prepare_to_join $1 "$(snap_cluster_add) ${@:2}"
    snap_join_cluster $1
}

function snap_enable_observability () {
    juju::model exec -u mk8s-cp/leader --wait 1000s -- "$(cat <<EOF
set -eu
export \$(grep -v '^#' /etc/environment | xargs)
microk8s enable storage dns rbac
microk8s status --wait-ready --timeout=600
microk8s enable observability
EOF
)"
}

juju::create_model
docker_registry_deploy
docker_registry_load_images
scale_application mk8s-cp 3 "${MK8S_CP_CONSTRAINTS}"
snap_cluster_application mk8s-cp
snap_enable_observability
scale_application mk8s-kw 10 "${MK8S_KW_CONSTRAINTS}"
snap_cluster_application mk8s-kw --worker
