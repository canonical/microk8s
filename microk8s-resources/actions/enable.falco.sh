#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

microk8s enable dns

NAMESPACE_PTR="sysdig-agent"

MANIFEST_PTR="https://raw.githubusercontent.com/draios/sysdig-cloud-scripts/master/agent_deploy/kubernetes/sysdig-agent-service.yaml"

KUBECTL="$SNAP/kubectl --kubeconfig=${SNAP_DATA}/credentials/client.config"

microk8s enable helm3

# make sure the "sysdigagent" namespace exists
$KUBECTL create namespace "$NAMESPACE_PTR" > /dev/null 2>&1 || true

# load the CRD and wait for it to be installed
$KUBECTL apply -f "$MANIFEST_PTR" -n "$NAMESPACE_PTR"

echo "Enabling Auditlogging using webhook"
mkdir -p "${SNAP_DATA}/args/auditlogging" >/dev/null 2>&1
cp "${SNAP}/actions/kube-api-audit.yaml" "${SNAP_DATA}/args/auditlogging"
cp "${SNAP}/actions/webhook-config.yaml" "${SNAP_DATA}/args/auditlogging"
echo "Reconfiguring apiserver"
refresh_opt_in_config "audit-log-maxbackup" "3" kube-apiserver
refresh_opt_in_config "audit-log-maxsize" "1024" kube-apiserver
refresh_opt_in_config "audit-log-maxage" "30" kube-apiserver
refresh_opt_in_config "audit-log-path" "/var/log/kube-apiserver-audit.log" kube-apiserver
refresh_opt_in_config "audit-policy-file" "${SNAP_DATA}/args/auditlogging/kube-api-audit.yaml" kube-apiserver
refresh_opt_in_config "audit-webhook-config-file" "${SNAP_DATA}/args/auditlogging/webhook-config-falco.yaml" kube-apiserver
refresh_opt_in_config "audit-webhook-batch-max-wait" "5s" kube-apiserver
AGENT_SERVICE_CLUSTERIP="$($KUBECTL get svc sysdig-agent -o=jsonpath={.spec.clusterIP} -n sysdig-agent)" envsubst < "${SNAP_DATA}/args/auditlogging/webhook-config.yaml" > "${SNAP_DATA}/args/auditlogging/webhook-config-falco.yaml"
#run_with_sudo preserve_env snapctl restart "${SNAP_NAME}.daemon-apiserver"
restart_service apiserver

start_timer="$(date +%s)"
timeout="120"
  
while ! (is_apiserver_ready) 
do
  sleep 5
  now="$(date +%s)"
  if [[ "$now" > "$(($start_timer + $timeout))" ]] ; then
    break
  fi
done

echo "Auditlogging  is enabled"

NAMESPACE_PTR1="falco"
# make sure the "falco" namespace exists
$KUBECTL create namespace "$NAMESPACE_PTR1" > /dev/null 2>&1 || true

microk8s helm3 repo add falcosecurity https://falcosecurity.github.io/charts
microk8s helm3 repo update 
#microk8s helm3 install -n "$NAMESPACE_PTR1" falco --set falco.jsonOutput=true --set falco.jsonIncludeOutputProperty=true --set falco.httpOutput.enabled=true --set falco.httpOutput.url="http://falcosidekick:2801/" falcosecurity/falco
microk8s helm3 install falco falcosecurity/falco -n "$NAMESPACE_PTR1" --set falco.jsonOutput=true --set falco.jsonIncludeOutputProperty=true --set falco.httpOut.enabled=true --set falcosidekick.enabled=true --set falcosidekick.config.debug=true  $@
sleep 15
echo "Falco is enabled"
#microk8s helm3 install -n "$NAMESPACE_PTR1" falcosidekick --set config.debug=true $@   falcosecurity/falcosidekick 
echo "Falcosidekick is enabled"
