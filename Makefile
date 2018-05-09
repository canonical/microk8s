KUBE_VERSION=$(shell curl -L https://dl.k8s.io/release/stable.txt)
KUBE_ARCH=amd64
ETCD_VERSION=v3.3.4
CNI_VERSION=v0.6.0

ifndef VERBOSE
	MAKEFLAGS += --no-print-directory
endif

build = ./build-scripts/build-microk8s

.PHONY: microk8s

default:
	@KUBE_VERSION=${KUBE_VERSION} KUBE_ARCH="${KUBE_ARCH}" ETCD_VERSION="${ETCD_VERSION}" CNI_VERSION="${CNI_VERSION}" ${build} 

clean:
	@rm -rf build
