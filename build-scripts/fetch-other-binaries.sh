#!/bin/bash
set -eu

mkdir -p $KUBE_SNAP_BINS
(cd $KUBE_SNAP_BINS
  curl -LO https://github.com/coreos/etcd/releases/download/${ETCD_VERSION}/etcd-${ETCD_VERSION}-linux-$KUBE_ARCH.tar.gz
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
    mkdir knative-yaml
    curl -L https://github.com/knative/serving/releases/download/$KNATIVE_SERVING_VERSION/serving.yaml -o ./knative-yaml/serving.yaml
    curl -L https://github.com/knative/eventing/releases/download/$KNATIVE_EVENTING_VERSION/release.yaml  -o ./knative-yaml/release.yaml
    curl -L https://github.com/knative/serving/releases/download/$KNATIVE_SERVING_VERSION/monitoring.yaml  -o ./knative-yaml/monitoring.yaml

    # This patch should be removed as soon as https://github.com/knative/serving/issues/5599 is fixed
    sed -i 's@extensions/v1beta1@apps/v1@g'  ./knative-yaml/monitoring.yaml
    sed -i '570 i \ \ selector:\n    matchLabels:\n      app: kube-state-metrics' ./knative-yaml/monitoring.yaml
    sed -i '6985 i \ \ selector:\n    matchLabels:\n      app: node-exporter' ./knative-yaml/monitoring.yaml
  fi
)
