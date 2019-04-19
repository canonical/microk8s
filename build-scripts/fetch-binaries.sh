#!/bin/bash
set -eu

apps="kubectl kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy"
export KUBE_SNAP_BINS=build/kube_bins/$KUBE_VERSION
mkdir -p $KUBE_SNAP_BINS
echo $KUBE_VERSION > $KUBE_SNAP_BINS/version
(cd $KUBE_SNAP_BINS
  for app in $apps; do
    mkdir -p $KUBE_ARCH
    (cd $KUBE_ARCH
      echo "Fetching $app $KUBE_VERSION $KUBE_ARCH"
      curl -LO \
        https://dl.k8s.io/${KUBE_VERSION}/bin/linux/$KUBE_ARCH/$app
      chmod +x $app
      if ! file ${app} 2>&1 | grep -q 'executable'; then
        echo "${app} is not an executable"
        exit 1
      fi
    )
  done

  curl -LO https://github.com/coreos/etcd/releases/download/${ETCD_VERSION}/etcd-${ETCD_VERSION}-linux-$KUBE_ARCH.tar.gz
  gzip -d etcd-${ETCD_VERSION}-linux-$KUBE_ARCH.tar.gz
  tar -xvf etcd-${ETCD_VERSION}-linux-$KUBE_ARCH.tar
  mv etcd-${ETCD_VERSION}-linux-$KUBE_ARCH etcd

  mkdir -p cni
  curl -LO https://github.com/containernetworking/plugins/releases/download/${CNI_VERSION}/cni-plugins-$KUBE_ARCH-${CNI_VERSION}.tgz
  tar -zxvf cni-plugins-$KUBE_ARCH-${CNI_VERSION}.tgz -C cni

  # Istio is released only on amd64
  if [ "$KUBE_ARCH" = "amd64" ]
  then
    ISTIO_ERSION=$(echo $ISTIO_VERSION | sed 's/v//g')
    curl -LO https://github.com/istio/istio/releases/download/${ISTIO_ERSION}/istio-${ISTIO_ERSION}-linux.tar.gz
    gzip -d istio-${ISTIO_ERSION}-linux.tar.gz
    tar -xvf istio-${ISTIO_ERSION}-linux.tar
    mv istio-${ISTIO_ERSION}/bin/istioctl .
    mkdir istio-yaml
    mv istio-${ISTIO_ERSION}/install/kubernetes/helm/istio/templates/crds.yaml ./istio-yaml/
    mv istio-${ISTIO_ERSION}/install/kubernetes/istio-demo-auth.yaml ./istio-yaml/
    mv istio-${ISTIO_ERSION}/install/kubernetes/istio-demo.yaml ./istio-yaml/ 
  fi
)
