#!/bin/bash
set -eux

apps="kubectl kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy"
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
)
