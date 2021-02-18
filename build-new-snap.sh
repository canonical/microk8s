#!/bin/bash

set -x

(cd $GOPATH/src/github.com/kubernetes/kubernetes/
  make WHAT="cmd/kubelite" GOFLAGS=-tags=libsqlite3,dqlite CGO_CFLAGS="-I/usr/include/" CGO_LDFLAGS="-L/lib" KUBE_CGO_OVERRIDES=kubelite
)
cp $GOPATH/src/github.com/kubernetes/kubernetes/_output/bin/kubelite ./squashfs-root/
rm -rf s.snap
mksquashfs ./squashfs-root/ s.snap
sudo snap install ./s.snap --classic --dangerous
