#!/usr/bin/env bash
set -eu

# This will be used by `microk8s --version`, which expects json format
echo "{\"kube\":\"${KUBE_VERSION}\",\"cni\":\"${CNI_VERSION}\"}"