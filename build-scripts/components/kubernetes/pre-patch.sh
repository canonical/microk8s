#!/bin/bash -x

# Ensure clean Kubernetes version
KUBE_ROOT="${PWD}"
source "${KUBE_ROOT}/hack/lib/version.sh"
kube::version::get_version_vars
kube::version::save_version_vars "${PWD}/.version.sh"
