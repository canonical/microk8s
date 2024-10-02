#!/usr/bin/env bash

INSPECT_DUMP=${SNAP_DATA}/inspection-report
RETURN_CODE=0
JOURNALCTL_LIMIT=100000

source $SNAP/actions/common/utils.sh

function print_help {
  # Print the help message
  printf -- 'This script will inspect your microk8s installation. It will report any issue it finds,\n';
  printf -- 'and create a tarball of logs and traces which can be attached to an issue filed against\n';
  printf -- 'the microk8s project.\n';
}


function check_service {
  # Check the service passed as the first argument is up and running and collect its logs.
  local service=$1
  mkdir -p $INSPECT_DUMP/$service

  status="inactive"
  if is_strict
  then
    journalctl -n $JOURNALCTL_LIMIT -u snap.$service &> $INSPECT_DUMP/$service/journal.log
    snapctl services $service &> $INSPECT_DUMP/$service/snapctl.log
    if ! snapctl services $service | grep inactive &> /dev/null
    then
      status="active"
    fi
  else
    journalctl -n $JOURNALCTL_LIMIT -u $service &> $INSPECT_DUMP/$service/journal.log
    systemctl status $service &> $INSPECT_DUMP/$service/systemctl.log
    if systemctl status $service &> /dev/null
    then
      status="active"
    fi
  fi

  if [ "$status" == "active" ]
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
  if is_strict
  then
    journalctl -k &> $INSPECT_DUMP/apparmor/dmesg
  else
    if [ -f /etc/apparmor.d/containerd ]
    then
      cp /etc/apparmor.d/containerd $INSPECT_DUMP/apparmor/
    fi
    dmesg &> $INSPECT_DUMP/apparmor/dmesg
    aa-status &> $INSPECT_DUMP/apparmor/aa-status
  fi
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
  ip addr &> $INSPECT_DUMP/network/ip-addr
  ip route &> $INSPECT_DUMP/network/ip-route
  iptables -t nat -L -n -v &> $INSPECT_DUMP/network/iptables
  iptables -S &> $INSPECT_DUMP/network/iptables-S
  iptables -L &> $INSPECT_DUMP/network/iptables-L
  if ! is_strict
  then
    ss -pln &> $INSPECT_DUMP/network/ss
  fi
}


function store_sys {
  # Generate sys directory
  mkdir -p $INSPECT_DUMP/sys
  # collect the processes running
  printf -- '  Copy processes list to the final report tarball\n'
  ps -ef > $INSPECT_DUMP/sys/ps
  # Store disk usage information
  printf -- '  Copy disk usage information to the final report tarball\n'
  df -h | grep ^/ &> $INSPECT_DUMP/sys/disk_usage # remove the grep to also include virtual in-memory filesystems
  # Store memory usage information
  printf -- '  Copy memory usage information to the final report tarball\n'
  free -m &> $INSPECT_DUMP/sys/memory_usage
  # Store server's uptime.
  printf -- '  Copy server uptime to the final report tarball\n'
  uptime &> $INSPECT_DUMP/sys/uptime
  # Store openssl information.
  printf -- '  Copy openSSL information to the final report tarball\n'
  openssl version -v -d -e &> $INSPECT_DUMP/sys/openssl
  if ! is_strict
  then
    printf -- '  Copy snap list to the final report tarball\n'
    snap version > $INSPECT_DUMP/sys/snap-version
    snap list > $INSPECT_DUMP/sys/snap-list
    # Stores VM name (or none, if we are not on a VM)
    printf -- '  Copy VM name (or none) to the final report tarball\n'
    systemd-detect-virt &> $INSPECT_DUMP/sys/vm_name
    # Store the current linux distro.
    printf -- '  Copy current linux distribution to the final report tarball\n'
    lsb_release -a &> $INSPECT_DUMP/sys/lsb_release
    # Store the aio request limits and current number
    # Returns sysctl: permission denied on key 'fs.aio-max-nr' on strict
    printf -- '  Copy asnycio usage and limits to the final report tarball\n'
    sysctl fs.aio-max-nr &> $INSPECT_DUMP/sys/aio-max-nr
    sysctl fs.aio-nr &> $INSPECT_DUMP/sys/aio-nr
    # Store the max inotify parameters
    printf -- '  Copy inotify max_user_instances and max_user_watches to the final report tarball\n'
    sysctl fs.inotify.max_user_instances &> $INSPECT_DUMP/sys/inotify_max_user_instances
    sysctl fs.inotify.max_user_watches &> $INSPECT_DUMP/sys/inotify_max_user_watches
  fi
}


function store_kubernetes_info {
  # Collect some in-k8s details
  printf -- '  Inspect kubernetes cluster\n'
  mkdir -p $INSPECT_DUMP/k8s
  if is_strict
  then
    export KUBECONFIG=$SNAP_DATA/credentials/client.config
    $SNAP/kubectl version > $INSPECT_DUMP/k8s/version 2>&1
    $SNAP/kubectl cluster-info > $INSPECT_DUMP/k8s/cluster-info 2>&1
    $SNAP/kubectl cluster-info dump -A > $INSPECT_DUMP/k8s/cluster-info-dump 2>&1
    $SNAP/kubectl get all --all-namespaces -o wide > $INSPECT_DUMP/k8s/get-all 2>&1
    $SNAP/kubectl get pv > $INSPECT_DUMP/k8s/get-pv 2>&1
    $SNAP/kubectl get pvc --all-namespaces > $INSPECT_DUMP/k8s/get-pvc 2>&1
  else
    sudo -E /snap/bin/microk8s kubectl version 2>&1 | sudo tee $INSPECT_DUMP/k8s/version > /dev/null
    sudo -E /snap/bin/microk8s kubectl cluster-info 2>&1 | sudo tee $INSPECT_DUMP/k8s/cluster-info > /dev/null
    sudo -E /snap/bin/microk8s kubectl cluster-info dump -A 2>&1 | sudo tee $INSPECT_DUMP/k8s/cluster-info-dump > /dev/null
    sudo -E /snap/bin/microk8s kubectl get all --all-namespaces -o wide 2>&1 | sudo tee $INSPECT_DUMP/k8s/get-all > /dev/null
    sudo -E /snap/bin/microk8s kubectl get pv 2>&1 | sudo tee $INSPECT_DUMP/k8s/get-pv > /dev/null # 2>&1 redirects stderr and stdout to /dev/null if no resources found
    sudo -E /snap/bin/microk8s kubectl get pvc --all-namespaces 2>&1 | sudo tee $INSPECT_DUMP/k8s/get-pvc > /dev/null # 2>&1 redirects stderr and stdout to /dev/null if no resources found
  fi

  # Collect bill of materials
  cp $SNAP/bom.json $INSPECT_DUMP/bom.json
}

function check_storage_addon {
  export KUBECONFIG=$SNAP_DATA/credentials/client.config
  image="$($SNAP/kubectl get deploy -n kube-system hostpath-provisioner -o jsonpath='{.spec.template.spec.containers[0].image}' 2>&1)"

  case "$image" in
    cdkbot/hostpath-provisioner-amd64:1.0.0|cdkbot/hostpath-provisioner-arm64:1.0.0)
      printf -- '\n'
      printf -- '\033[0;33mWARNING: \033[0m You are using an outdated version of the hostpath-provisioner.\n'
      printf -- 'Existing PersistentVolumes are not affected, but you may be unable to create new ones.\n'
      printf -- "Image currently in use: ${image}\n"
      printf -- '\n'
      printf -- 'Consider updating the hostpath-provisioner with:\n'
      printf -- '    microk8s disable hostpath-storage\n'
      printf -- '    microk8s enable hostpath-storage\n'
      printf -- '\n'
      ;;
  esac
}


function store_dqlite_info {
  # Collect some dqlite details
  printf -- '  Inspect dqlite\n'
  mkdir -p $INSPECT_DUMP/dqlite
  run_with_sudo preserve_env cp ${SNAP_DATA}/var/kubernetes/backend/cluster.yaml $INSPECT_DUMP/dqlite/
  run_with_sudo preserve_env cp ${SNAP_DATA}/var/kubernetes/backend/localnode.yaml $INSPECT_DUMP/dqlite/
  run_with_sudo preserve_env cp ${SNAP_DATA}/var/kubernetes/backend/info.yaml $INSPECT_DUMP/dqlite/
  run_with_sudo preserve_env ls -lh ${SNAP_DATA}/var/kubernetes/backend/ 2>&1 >  $INSPECT_DUMP/dqlite/list.out
}


function suggest_fixes {
  # Propose fixes
  printf '\n'
  # This if is verbose but I hope is clear
  status="inactive"
  if is_strict
  then
    if ! snapctl services microk8s.daemon-kubelite | grep inactive &> /dev/null
    then
      status="active"
    fi
  else
    if systemctl status snap.microk8s.daemon-kubelite &> /dev/null
    then
      status="active"
    fi
  fi

  if [ "$status" == "inactive" ]
  then
    if lsof -Pi :16443 -sTCP:LISTEN -t &> /dev/null
    then
      printf -- '\033[0;33m WARNING: \033[0m Port 16443 seems to be in use by another application.\n'
    fi
  fi

  if iptables -L 2>&1 | grep FORWARD | grep DROP &> /dev/null
  then
    printf -- '\033[0;33m WARNING: \033[0m IPtables FORWARD policy is DROP. '
    printf -- 'Consider enabling traffic forwarding with: sudo iptables -P FORWARD ACCEPT \n'
    printf -- 'The change can be made persistent with: sudo apt-get install iptables-persistent\n'
  fi

  if ! is_strict && [ /snap/core20/current/usr/bin/which ufw &> /dev/null ]
  then
    if ufw status | grep -q "Status: active"
    then
      header='\033[0;33m WARNING: \033[0m Firewall is enabled. Consider allowing pod traffic with: \n'
      content=''
      if ! echo $ufw | grep -q vxlan.calico
      then
        content+='  sudo ufw allow in on vxlan.calico && sudo ufw allow out on vxlan.calico\n'
      fi
      if ! echo $ufw | grep 'cali+' &> /dev/null
      then
        content+='  sudo ufw allow in on cali+ && sudo ufw allow out on cali+\n'
      fi

      if [[ ! -z "$content" ]]
      then
        echo printing
        printf -- "$header"
        printf -- "$content"
      fi
    fi
  fi

  # check for selinux. if enabled, print warning.
  if getenforce 2>&1 | grep 'Enabled' > /dev/null
  then
    printf -- '\033[0;33m WARNING: \033[0m SElinux is enabled. Consider disabling it.\n'
  fi

  # check for docker
  # if docker is installed
  if [ -d "/etc/docker/" ] && ! [ -z "$(which dockerd)" ]; then
    # if docker/daemon.json file doesn't exist print prompt to create it and mark the registry as insecure
    if [ ! -f "/etc/docker/daemon.json" ]; then
      printf -- '\033[0;33mWARNING: \033[0m Docker is installed. \n'
      printf -- 'File "/etc/docker/daemon.json" does not exist. \n'
      printf -- 'You should create it and add the following lines: \n'
      printf -- '{\n'
      printf -- '    "insecure-registries" : ["localhost:32000"] \n'
      printf -- '}\n'
      printf -- 'and then restart docker with: sudo systemctl restart docker\n'
    # else if the file docker/daemon.json exists
    else
      # if it doesn't include the registry as insecure, prompt to add the following lines
      if ! grep -qs localhost:32000 /etc/docker/daemon.json
      then
        printf -- '\033[0;33mWARNING: \033[0m Docker is installed. \n'
        printf -- 'Add the following lines to /etc/docker/daemon.json: \n'
        printf -- '{\n'
        printf -- '    "insecure-registries" : ["localhost:32000"] \n'
        printf -- '}\n'
        printf -- 'and then restart docker with: sudo systemctl restart docker\n'
      fi
    fi
  fi

  if ! grep -q 'cgroup/memory' /proc/self/mountinfo; then
    if ! grep -q 'cgroup2' /proc/self/mountinfo; then
      if ! mount -t cgroup2 | grep -q 'type cgroup2'; then
        printf -- '\033[0;33mWARNING: \033[0m The memory cgroup is not enabled. \n'
        printf -- 'The cluster may not be functioning properly. Please ensure cgroups are enabled \n'
        printf -- 'See for example: https://microk8s.io/docs/install-alternatives#heading--arm \n'
      fi
    fi
  fi

  # Fedora Specific Checks
  if ! is_strict && fedora_release
  then

    # Check if appropriate cgroup libraries for Fedora are installed
    if ! rpm -q libcgroup &> /dev/null
    then
      printf -- '\033[31m FAIL: \033[0m libcgroup v1 is not installed. Please install it\n'
      printf -- '\twith: dnf install libcgroup libcgroup-tools \n'
    fi

    # check if cgroups v1 is supported
    if [ ! -d "/sys/fs/cgroup/memory" ] &> /dev/null
    then
      printf -- '\033[31m FAIL: \033[0m Cgroup v1 seems not to be enabled. Please enable it \n'
      printf -- '\tby executing the following command and reboot: \n'
      printf -- '\tgrubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=0" \n'
    fi
  fi

  # Debian 9 checks
  if ! is_strict && debian9_release
  then

    # Check if snapctl is fresh
    if ! [ -L "/usr/bin/snapctl" ]
    then
      printf -- '\033[0;33mWARNING: \033[0m On Debian 9 the snapctl binary if outdated. Replace it with: \n'
      printf -- '\t sudo snap install core \n'
      printf -- '\t sudo mv /usr/bin/snapctl /usr/bin/snapctl.old \n'
      printf -- '\t sudo ln -s  /snap/core/current/usr/bin/snapctl /usr/bin/snapctl \n'
    fi
  fi

  # LXD Specific Checks
  if ! is_strict && cat /proc/1/environ | grep "container=lxc" &> /dev/null
    then

    # make sure the /dev/kmsg is available, indicating a potential missing profile
    if [ ! -c "/dev/kmsg" ]  # kmsg is a character device
    then
      printf -- '\033[0;33mWARNING: \033[0m the lxc profile for MicroK8s might be missing. \n'
      printf -- '\t  Refer to this help document to get MicroK8s working in with LXD: \n'
      printf -- '\t  https://microk8s.io/docs/lxd \n'
    fi
  fi

  # node name
  nodename="$(hostname)"
  if [[ "$nodename" =~ [A-Z|_] ]] && ! grep -e "hostname-override" "${SNAP_DATA}/args/kubelet" &> /dev/null
  then
    printf -- "\033[0;33mWARNING: \033[0m This machine's hostname contains capital letters and/or underscores. \n"
    printf -- "\t  This is not a valid name for a Kubernetes node, causing node registration to fail.\n"
    printf -- "\t  Please change the machine's hostname or refer to the documentation for more details: \n"
    printf -- "\t  https://microk8s.io/docs/troubleshooting#heading--common-issues \n"
  fi

  if grep Raspberry /proc/cpuinfo -q &&
    [ -e /etc/os-release ] &&
    grep impish /etc/os-release -q &&
    ! dpkg -l | grep linux-modules-extra-raspi -q
  then
    printf -- "\033[0;33mWARNING: \033[0m On Raspberry Pi consider installing the linux-modules-extra-raspi package with: \n"
    printf -- "\t  'sudo apt install linux-modules-extra-raspi' and reboot.\n"
  fi

  if ! [ -f /proc/sys/net/bridge/bridge-nf-call-iptables ]
  then
    printf -- "\033[0;33mWARNING: \033[0m Please ensure br_netfilter kernel module is loaded on the host. \n"
  fi

  if ! ( ip route; ip -6 route ) | grep "^default" &>/dev/null
  then
    printf -- "
\033[0;33mWARNING: \033[0m No default route exists. MicroK8s might not work properly.
Refer to https://microk8s.io/docs for instructions on air-gap deployments.\n\n
"
  fi

  if ! is_strict
  then
    AIO_MAX_NR=$(sysctl -n fs.aio-max-nr)
    AIO_NR=$(sysctl -n fs.aio-nr)
    if [ "$AIO_NR" -ge "$AIO_MAX_NR" ]; then
      printf -- "\033[0;33mWARNING: \033[0m Available asyncio requests are exhausted. This might lead to dqlite being unresponsive. \n"
      printf -- "\t  Increase the limit and restart the k8s-dqlite service with: \n"
      printf -- "\t  \t echo fs.aio.max-nr=1048576 | sudo tee -a /etc/sysctl.conf\n"
      printf -- "\t  \t sudo sysctl --system\n"
      printf -- "\t  \t sudo snap restart microk8s.daemon-k8s-dqlite\n"
    fi

    MAX_USER_INSTANCES=$(sysctl -n fs.inotify.max_user_instances)
    if [ "$MAX_USER_INSTANCES" -lt 1024 ]; then
      printf -- "\033[0;33mWARNING: \033[0m Maximum number of inotify user instances is less than the recommended value of 1024. \n"
      printf -- "\t  Increase the limit with: \n"
      printf -- "\t  \t echo fs.inotify.max_user_instances=1024 | sudo tee -a /etc/sysctl.conf\n"
      printf -- "\t  \t sudo sysctl --system\n"
    fi

    MAX_USER_WATCHES=$(sysctl -n fs.inotify.max_user_watches)
    if [ "$MAX_USER_WATCHES" -lt 1048576  ]; then
      printf -- "\033[0;33mWARNING: \033[0m Maximum number of inotify user watches is less than the recommended value of 1048576. \n"
      printf -- "\t  Increase the limit with: \n"
      printf -- "\t  \t echo fs.inotify.max_user_watches=1048576 | sudo tee -a /etc/sysctl.conf\n"
      printf -- "\t  \t sudo sysctl --system\n"
    fi
  fi
}

function fedora_release {
  local RELEASE=`cat /etc/os-release | grep "^NAME=" | cut -f2 -d=`
  if [ "${RELEASE}" == "Fedora" ]
  then
    return 0
  else
    return 1
  fi
}

function debian9_release {
  if [ -e /etc/debian_version ] &&
     grep "9\." /etc/debian_version -q
  then
    return 0
  else
    return 1
  fi
}

function build_report_tarball {
  # Tar and gz the report
  local now_is=$(date +"%Y%m%d_%H%M%S")
  tar -C ${SNAP_DATA} -cf ${SNAP_DATA}/inspection-report-${now_is}.tar inspection-report &> /dev/null
  gzip ${SNAP_DATA}/inspection-report-${now_is}.tar
  printf -- '  Report tarball is at %s/inspection-report-%s.tar.gz\n' "${SNAP_DATA}" "${now_is}"
}

function check_certificates {
  exp_date_str="$(openssl x509 -enddate -noout -in "${SNAP_DATA}/certs/ca.crt" | cut -d= -f 2)"
  exp_date_secs="$(date -d "$exp_date_str" +%s)"
  now_secs=$(date +%s)
  difference=$(($exp_date_secs-$now_secs))
  days=$(($difference/(3600*24)))
  if [ "3" -ge $days ];
  then
    printf -- '\033[0;33mWARNING: \033[0m This deployments certificates will expire in $days days. \n'
    printf -- 'Either redeploy MicroK8s or attempt a refresh with "microk8s refresh-certs"\n'
  fi
}

function check_memory {
  MEMORY=`cat /proc/meminfo | grep MemTotal | awk '{ print $2 }'`
  if [ $MEMORY -le 524288 ]
  then
    printf -- "\033[0;33mWARNING: \033[0m This system has ${MEMORY} bytes of RAM available.\n"
    printf -- "It may not be enough to run the Kubernetes control plane services.\n"
    printf -- "Consider joining as a worker-only to a cluster.\n"
  fi
}

function check_low_memory_guard {
  if [ -e "${SNAP_DATA}/var/lock/low-memory-guard.lock" ]
  then
    printf -- '\033[0;33mWARNING: \033[0m The low memory guard is enabled.\n'
    printf -- 'This is to protect the server from running out of memory.\n'
    printf -- 'Consider joining as a worker-only to a cluster.\n'
    printf -- '\n'
    printf -- 'Alternatively, to disable the low memory guard, start MicroK8s with:\n'
    printf -- '\n'
    printf -- '    microk8s start --disable-low-memory-guard\n'
  fi
}

function check_hostname {
  HOST=$(hostname)
  if echo "${HOST}" | grep -q "[A-Z]" 2> /dev/null
  then
    printf -- "\033[0;33mWARNING: \033[0m The hostname of this server is '${HOST}'.\n"
    printf -- "Having uppercase letters in the hostname may cause issues with RBAC.\n"
    printf -- "Consider changing the hostname to only have lowercase letters with:\n"
    printf -- "\n"
    printf -- "    hostnamectl set-hostname $(echo ${HOST} | tr '[:upper:]' '[:lower:]')\n"
  fi
}

if [[ (${#@} -ne 0) && (("$*" == "--help") || ("$*" == "-h")) ]]; then
  print_help
  exit 0;
fi;

exit_if_not_root

rm -rf ${SNAP_DATA}/inspection-report
mkdir -p ${SNAP_DATA}/inspection-report

printf -- 'Inspecting system\n'
check_memory
check_low_memory_guard
check_hostname

printf -- 'Inspecting Certificates\n'
check_certificates

printf -- 'Inspecting services\n'
svc_cluster_agent="microk8s.daemon-cluster-agent"
svc_containerd="microk8s.daemon-containerd"
svc_kubelite="microk8s.daemon-kubelite"
svc_flanneld="microk8s.daemon-flanneld"
svc_etcd="microk8s.daemon-etcd"
svc_dqlite="microk8s.daemon-k8s-dqlite"
svc_api_server_proxy="microk8s.daemon-apiserver-proxy"
svc_api_server_kicker="microk8s.daemon-apiserver-kicker"

if ! is_strict
then
  svc_cluster_agent="snap.${svc_cluster_agent}"
  svc_containerd="snap.${svc_containerd}"
  svc_kubelite="snap.${svc_kubelite}"
  svc_flanneld="snap.${svc_flanneld}"
  svc_etcd="snap.${svc_etcd}"
  svc_dqlite="snap.${svc_dqlite}"
  svc_api_server_proxy="snap.${svc_api_server_proxy}"
  svc_api_server_kicker="snap.${svc_api_server_kicker}"
fi

check_service $svc_cluster_agent
check_service $svc_containerd
check_service $svc_kubelite

if ! [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
then
  check_service $svc_flanneld
  check_service $svc_etcd
else
  if ! [ -e "${SNAP_DATA}/var/lock/no-k8s-dqlite" ]
  then
    # workers do not run dqlite
    check_service $svc_dqlite
  fi
fi

if ! [ -e "${SNAP_DATA}/var/lock/no-apiserver-proxy" ]
then
  check_service $svc_api_server_proxy
fi

if ! [ -e ${SNAP_DATA}/var/lock/clustered.lock ]
then
  check_service $svc_api_server_kicker
fi

store_args

printf -- 'Inspecting AppArmor configuration\n'
check_apparmor

printf -- 'Gathering system information\n'
store_sys
store_network

printf -- 'Inspecting kubernetes cluster\n'
store_kubernetes_info
check_storage_addon

if [ -e "${SNAP_DATA}/var/lock/ha-cluster" ]
then
  printf -- 'Inspecting dqlite\n'
  store_dqlite_info
fi

suggest_fixes

printf -- 'Building the report tarball\n'
build_report_tarball

exit $RETURN_CODE
