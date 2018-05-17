#!/bin/bash

set -eux

# write microk8s kubeconfig to a location where ksonnet can use it
microk8s.kubectl config view > $HOME/.kube/config


# need to make your own GH token with public read and use it here, or
# you'll get rate-limit errors installing kubeflow
GITHUB_TOKEN=


# install ksonnet
KS_VERSION="0.10.2"
platform="linux"
ksonnet_repo="https://github.com/ksonnet/ksonnet/releases/download/v$KS_VERSION"
ksonnet_file="ks_${KS_VERSION}_${platform}_amd64.tar.gz"
work_dir="$(mktemp -d)"
curl -fsSL -o "$work_dir/$ksonnet_file" "$ksonnet_repo/$ksonnet_file"
tar -C "$work_dir" -zxvf "$work_dir/$ksonnet_file" 1>&2
mkdir -p $HOME/bin
mv "$work_dir/ks_${KS_VERSION}_${platform}_amd64/ks" "$HOME/bin/ks"
export PATH=$PATH:$HOME/bin
hash -r
rm -rf "$work_dir"


# install kubeflow
mkdir -p $HOME/.local/share/kubeflow
cd $HOME/.local/share/kubeflow
microk8s.kubectl create ns kubeflow
PROJECT=kubeflow.$(mktemp -d)
ks init $PROJECT
cd $PROJECT
ks env add cdk
ks registry add kubeflow github.com/google/kubeflow/tree/master/kubeflow
ks pkg install kubeflow/core
ks pkg install kubeflow/tf-serving
ks pkg install kubeflow/tf-job
ks generate core kubeflow-core --name=kubeflow-core --namespace=kubeflow
ks apply cdk -c kubeflow-core



