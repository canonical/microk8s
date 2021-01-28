#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

microk8s helm3  uninstall falcosidekick

microk8s helm3  uninstall falco

NAMESPACE_PTR="sysdig-agent"

MANIFEST_PTR="https://raw.githubusercontent.com/draios/sysdig-cloud-scripts/master/agent_deploy/kubernetes/sysdig-agent-service.yaml"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

KUBECTL_DELETE_ARGS="--wait=true --timeout=180s --ignore-not-found=true"

echo "Disabling sysdig-agent"

# unload the the manifests
$KUBECTL delete $KUBECTL_DELETE_ARGS -n $NAMESPACE_PTR -f "$MANIFEST_PTR" > /dev/null 2>&1

# delete the "sysdigagent" namespace
$KUBECTL delete $KUBECTL_DELETE_ARGS namespace "$NAMESPACE_PTR" > /dev/null 2>&1 || true

echo "sysdigagent is disabled"


skip_opt_in_config "audit-log-maxbackup"  kube-apiserver
skip_opt_in_config "audit-log-maxsize"  kube-apiserver
skip_opt_in_config "audit-log-maxage"  kube-apiserver
skip_opt_in_config "audit-policy-file"  kube-apiserver
skip_opt_in_config "audit-log-path"  kube-apiserver
skip_opt_in_config "audit-webhook-config-file"  kube-apiserver
skip_opt_in_config "audit-webhook-batch-max-wait"  kube-apiserver
rm -rf "${SNAP_DATA}/args/auditlogging"

restart_service apiserver
apiserver=$(wait_for_service apiserver)
if [[ $apiserver == fail ]]
then
	  echo "Kubeapiserver did not start on time. Proceeding."
fi
sleep 15
echo "Falco is disabled"

