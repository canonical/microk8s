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
cp "${SNAP}/actions/kube-api-audit" "/var/snap/microk8s/current/args"
cp "${SNAP}/actions/webhook-config.yaml" "/var/snap/microk8s/current/args"
echo "Reconfiguring apiserver"
refresh_opt_in_config "audit-log-maxbackup" "3" kube-apiserver
refresh_opt_in_config "audit-log-maxsize" "1024" kube-apiserver
refresh_opt_in_config "audit-log-maxage" "30" kube-apiserver
refresh_opt_in_config "audit-log-path" "/var/log/kube-apiserver-audit.log" kube-apiserver
refresh_opt_in_config "audit-policy-file" "/var/snap/microk8s/current/args/kube-api-audit" kube-apiserver
refresh_opt_in_config "audit-webhook-config-file" "/var/snap/microk8s/current/args/webhook-config.yaml" kube-apiserver
refresh_opt_in_config "audit-webhook-batch-max-wait" "5s" kube-apiserver

run_with_sudo preserve_env snapctl restart "${SNAP_NAME}.daemon-apiserver"

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

microk8s helm3 repo add falcosecurity https://falcosecurity.github.io/charts
microk8s helm3 repo update 
microk8s helm3 install falco --set falco.jsonOutput=true --set falco.jsonIncludeOutputProperty=true --set falco.httpOutput.enabled=true --set falco.httpOutput.url="http://falcosidekick:2801/" falcosecurity/falco 
sleep 15
echo "Falco is enabled"
microk8s helm3 install falcosidekick --set config.debug=true falcosecurity/falcosidekick
echo "Falcosidkick is enabled"
