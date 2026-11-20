#!/bin/bash

KUBECONFIG="/var/snap/microk8s/current/credentials/client.config"
SONOBUOY_BIN=/home/user/go/bin/sonobuoy
E2E_EXTRA_ARGS="--non-blocking-taints=node-role.kubernetes.io/controller --ginkgo.v"
K8S_VERSION="v1.30.0"
CHANNEL="1.30/stable"
EXTRACT_DIR="results"
RESULTS_FILE="${EXTRACT_DIR}/plugins/e2e/results/global/e2e.log"

# This assumes the correct version of microk8s, sonobuoy and multipass are installed.
# For example if CHANNEL=1.30/stable the system should have microk8s 1.30.

function latest_tar_path() {
    ls -Art *.tar.gz | tail -n 1
}

function run_e2e() {
    "${SONOBUOY_BIN}" run \
    --plugin-env=e2e.E2E_EXTRA_ARGS="${E2E_EXTRA_ARGS}" \
    --mode=certified-conformance \
    --kubernetes-version="${K8S_VERSION}" \
    --kubeconfig "${KUBECONFIG}"
}

function extract_results() {
    ${SONOBUOY_BIN} retrieve --kubeconfig ${KUBECONFIG}
    mkdir -p "${EXTRACT_DIR}"
    tar xvf "$(latest_tar_path)" -C "${EXTRACT_DIR}"
}
