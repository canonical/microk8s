#!/bin/bash
set -ex

echo "Switching master to dqlite"

source $SNAP/actions/common/utils.sh

BACKUP_DIR="$SNAP_DATA/var/tmp/upgrades/001-switch-to-dqlite"
DB_DIR="$BACKUP_DIR/db"

mkdir -p "$BACKUP_DIR/args/"

echo "Configuring services"
${SNAP}/microk8s-stop.wrapper

cp "$SNAP_DATA"/args/kube-apiserver "$BACKUP_DIR/args"
# Configure the API sever to talk to the external dqlite
if [ -e ${SNAP}/default-args/k8s-dqlite ] &&
   ! [ -e ${SNAP_DATA}/args/k8s-dqlite ]
then
  echo "Reconfiguring the API server for dqlite"
  cp ${SNAP}/default-args/k8s-dqlite ${SNAP_DATA}/args/k8s-dqlite
fi

skip_opt_in_config storage-backend kube-apiserver
skip_opt_in_config storage-dir kube-apiserver

skip_opt_in_config "etcd-servers" kube-apiserver
skip_opt_in_config "etcd-cafile" kube-apiserver
skip_opt_in_config "etcd-certfile" kube-apiserver
skip_opt_in_config "etcd-keyfile" kube-apiserver

refresh_opt_in_config etcd-servers unix://\${SNAP_DATA}/var/kubernetes/backend/kine.sock:12379 kube-apiserver

cp "$SNAP_DATA"/args/etcd "$BACKUP_DIR/args"
cat <<EOT > "$SNAP_DATA"/args/etcd
--data-dir=\${SNAP_COMMON}/var/run/etcd
--advertise-client-urls=http://127.0.0.1:12379
--listen-client-urls=http://0.0.0.0:12379
--enable-v2=true
EOT

if ! [ -e "${SNAP_DATA}/var/kubernetes/backend/cluster.key" ]
then
  init_cluster
fi

snapctl restart ${SNAP_NAME}.daemon-k8s-dqlite
snapctl restart ${SNAP_NAME}.daemon-kubelite

run_etcd="$(is_service_expected_to_start etcd)"
if [ "${run_etcd}" == "1" ]
then
  snapctl start microk8s.daemon-etcd
  # TODO do some proper wait here
  sleep 15

  rm -rf "$DB_DIR"
  $SNAP/bin/k8s-dqlite migrator --mode backup --endpoint "http://127.0.0.1:12379" --db-dir "$DB_DIR" --debug
  chmod 600 "$DB_DIR"
  # Wait up to two minutes for the apiserver to come up.
  # TODO: this polling is not good enough. We should find a new way to ensure the apiserver is up.
  timeout="120"
  start_timer="$(date +%s)"
  while ! (is_apiserver_ready)
  do
    sleep 5
    now="$(date +%s)"
    if [[ "$now" > "$(($start_timer + $timeout))" ]] ; then
      break
    fi
  done

  # if the API server came up try to load the CNI manifest
  now="$(date +%s)"
  if [[ "$now" < "$(($start_timer + $timeout))" ]] ; then
    if (is_apiserver_ready)
    then
        $SNAP/bin/k8s-dqlite migrator --mode restore --endpoint "unix://${SNAP_DATA}/var/kubernetes/backend/kine.sock:12379" --db-dir "$DB_DIR" --debug
    fi
  fi

  sleep 10
  set_service_not_expected_to_start etcd
  snapctl stop microk8s.daemon-etcd
  set_service_expected_to_start k8s-dqlite
fi

rm -rf ${SNAP_DATA}/var/lock/cni-loaded
${SNAP}/microk8s-start.wrapper
${SNAP}/microk8s-status.wrapper --wait-ready --timeout 120

echo "Dqlite is enabled"
