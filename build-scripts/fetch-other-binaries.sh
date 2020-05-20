#!/bin/bash
set -eu

mkdir -p $KUBE_SNAP_BINS
(cd $KUBE_SNAP_BINS
  curl -LO https://github.com/etcd-io/etcd/releases/download/${ETCD_VERSION}/etcd-${ETCD_VERSION}-linux-$KUBE_ARCH.tar.gz
  gzip -d etcd-${ETCD_VERSION}-linux-$KUBE_ARCH.tar.gz
  tar -xvf etcd-${ETCD_VERSION}-linux-$KUBE_ARCH.tar
  mv etcd-${ETCD_VERSION}-linux-$KUBE_ARCH etcd

  mkdir -p cni
  curl -LO https://github.com/containernetworking/plugins/releases/download/${CNI_VERSION}/cni-plugins-$KUBE_ARCH-${CNI_VERSION}.tgz
  tar -zxvf cni-plugins-$KUBE_ARCH-${CNI_VERSION}.tgz -C cni

  mkdir -p flanneld
  curl -LO https://github.com/coreos/flannel/releases/download/${FLANNELD_VERSION}/flannel-${FLANNELD_VERSION}-linux-${KUBE_ARCH}.tar.gz
  tar -zxvf flannel-${FLANNELD_VERSION}-linux-${KUBE_ARCH}.tar.gz -C flanneld

  # Knative is released only on amd64
  if [ "$KUBE_ARCH" = "amd64" ]
  then
    # Knative, not quite binares but still fetcing.
    mkdir -p knative-yaml/setup
    curl -L https://github.com/knative/serving/releases/download/$KNATIVE_SERVING_VERSION/serving-crds.yaml -o ./knative-yaml/setup/serving-crds.yaml
    curl -L https://github.com/knative/serving/releases/download/$KNATIVE_SERVING_VERSION/serving-core.yaml -o ./knative-yaml/serving-core.yaml

    curl -L https://github.com/knative/eventing/releases/download/$KNATIVE_EVENTING_VERSION/eventing-crds.yaml -o ./knative-yaml/setup/eventing-crds.yaml
    curl -L https://github.com/knative/eventing/releases/download/$KNATIVE_EVENTING_VERSION/eventing-core.yaml -o ./knative-yaml/eventing-core.yaml
    curl -L https://github.com/knative/eventing/releases/download/$KNATIVE_EVENTING_VERSION/in-memory-channel.yaml -o ./knative-yaml/in-memory-channel.yaml
    curl -L https://github.com/knative/eventing/releases/download/$KNATIVE_EVENTING_VERSION/channel-broker.yaml -o ./knative-yaml/channel-broker.yaml
    curl -L https://github.com/knative/serving/releases/download/$KNATIVE_EVENTING_VERSION/monitoring-core.yaml -o ./knative-yaml/monitoring-core.yaml
  fi
)
