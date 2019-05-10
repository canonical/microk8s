#!/usr/bin/env bash

INSPECT_DUMP=${SNAP_DATA}/inspection-report
RETURN_CODE=0
JOURNALCTL_LIMIT=100000

function print_help {
  # Print the help message
  printf -- 'This script will inspect your microk8s installation. It will report any issue it finds,\n';
  printf -- 'and create a tarball of logs and traces which can be attached to an issue filed against\n';
  printf -- 'the microk8s project.\n';
}


function check_service {
  # Chec the service passed as the firsr argument is up and running and collect its logs.
  local service=$1
  mkdir -p $INSPECT_DUMP/$service
  journalctl -n $JOURNALCTL_LIMIT -u $service &> $INSPECT_DUMP/$service/journal.log
  systemctl status $service &> $INSPECT_DUMP/$service/systemctl.log
  if systemctl status $service &> /dev/null
  then
    printf -- '  Service %s is running\n' "$service"
  else
    printf -- '\033[31m FAIL: \033[0m Service %s is not running\n' "$service"
    printf -- 'For more details look at: sudo journalctl -u %s\n' "$service"
    RETURN_CODE=1
  fi
}


function check_apparmor {
  # Collect apparmor info.
  mkdir -p $INSPECT_DUMP/apparmor
  if [ -f /etc/apparmor.d/containerd ]
  then
    cp /etc/apparmor.d/containerd $INSPECT_DUMP/apparmor/
  fi
  dmesg &> $INSPECT_DUMP/apparmor/dmesg
  aa-status &> $INSPECT_DUMP/apparmor/aa-status
}


function store_args {
  # Collect the services arguments.
  printf -- '  Copy service arguments to the final report tarball\n'
  cp -r ${SNAP_DATA}/args $INSPECT_DUMP
}


function store_network {
  # Collect network setup.
  printf -- '  Copy network configuration to the final report tarball\n'
  mkdir -p $INSPECT_DUMP/network
  netstat -ln &> $INSPECT_DUMP/network/netstat
  ifconfig &> $INSPECT_DUMP/network/ifconfig
  iptables -t nat -L -n -v &> $INSPECT_DUMP/network/iptables
}


function store_processes {
  # Collect the processes running
  printf -- '  Copy processes list to the final report tarball\n'
  mkdir -p $INSPECT_DUMP/sys
  ps -ef > $INSPECT_DUMP/sys/ps
  printf -- '  Copy snap list to the final report tarball\n'
  snap version > $INSPECT_DUMP/sys/snap-version
  snap list > $INSPECT_DUMP/sys/snap-list
}


function store_kubernetes_info {
  # Collect some in-k8s details
  printf -- '  Inspect kubernetes cluster\n'
  mkdir -p $INSPECT_DUMP/k8s
  /snap/bin/microk8s.kubectl version | sudo tee $INSPECT_DUMP/k8s/version > /dev/null
  /snap/bin/microk8s.kubectl cluster-info | sudo tee $INSPECT_DUMP/k8s/cluster-info > /dev/null
  /snap/bin/microk8s.kubectl cluster-info dump | sudo tee $INSPECT_DUMP/k8s/cluster-info-dump > /dev/null
  /snap/bin/microk8s.kubectl get all --all-namespaces | sudo tee $INSPECT_DUMP/k8s/get-all > /dev/null
}


function suggest_fixes {
  # Propose fixes
  printf '\n'
  if ! systemctl status snap.microk8s.daemon-apiserver &> /dev/null
  then
    if lsof -Pi :8080 -sTCP:LISTEN -t &> /dev/null
    then
      printf -- '\033[0;33m WARNING: \033[0m Port 8080 seems to be in use by another application.\n'
    fi
  fi

  if iptables -L | grep FORWARD | grep DROP &> /dev/null
  then
      printf -- '\033[0;33m WARNING: \033[0m IPtables FORWARD policy is DROP. '
      printf -- 'Consider enabling traffic forwarding with: sudo iptables -P FORWARD ACCEPT \n'
      printf -- 'The change can be made persistent with: sudo apt-get install iptables-persistent\n'
  fi

  ufw=$(ufw status)
  if echo $ufw | grep "Status: active" &> /dev/null && ! echo $ufw | grep cbr0 &> /dev/null
  then
      printf -- '\033[0;33m WARNING: \033[0m Firewall is enabled. Consider allowing pod traffic '
      printf -- 'with: sudo ufw allow in on cbr0 && sudo ufw allow out on cbr0\n'
  fi
}


function build_report_tarball {
  # Tar and gz the report
  local now_is=$(date +"%Y%m%d_%H%M%S")
  tar -C ${SNAP_DATA} -cf ${SNAP_DATA}/inspection-report-${now_is}.tar inspection-report &> /dev/null
  gzip ${SNAP_DATA}/inspection-report-${now_is}.tar
  printf -- '  Report tarball is at %s/inspection-report-%s.tar.gz\n' "${SNAP_DATA}" "${now_is}"
}


if [ ${#@} -ne 0 ] && [ "${@#"--help"}" = "" ]; then
  print_help
  exit 0;
fi;

rm -rf ${SNAP_DATA}/inspection-report
mkdir -p ${SNAP_DATA}/inspection-report

printf -- 'Inspecting services\n'
check_service "snap.microk8s.daemon-containerd"
check_service "snap.microk8s.daemon-apiserver"
check_service "snap.microk8s.daemon-proxy"
check_service "snap.microk8s.daemon-kubelet"
check_service "snap.microk8s.daemon-scheduler"
check_service "snap.microk8s.daemon-controller-manager"
check_service "snap.microk8s.daemon-etcd"
store_args

printf -- 'Inspecting AppArmor configuration\n'
check_apparmor

printf -- 'Gathering system info\n'
store_network
store_processes
store_kubernetes_info

suggest_fixes

printf -- 'Building the report tarball\n'
build_report_tarball

exit $RETURN_CODE
