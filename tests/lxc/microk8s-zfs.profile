name: microk8s
config:
  boot.autostart: "true"
  linux.kernel_modules: ip_vs,ip_vs_rr,ip_vs_wrr,ip_vs_sh,nf_conntrack_ipv4,ip_tables,ip6_tables,netlink_diag,nf_nat,overlay
  raw.lxc: |
    lxc.apparmor.profile=unconfined
    lxc.mount.auto=proc:rw sys:rw cgroup:rw
    lxc.cgroup.devices.allow=a
    lxc.cap.drop=
  security.nesting: "true"
  security.privileged: "true"
description: ""
devices:
  aadisable:
    path: /sys/module/nf_conntrack/parameters/hashsize
    source: /sys/module/nf_conntrack/parameters/hashsize
    type: disk
  aadisable1:
    path: /sys/module/apparmor/parameters/enabled
    source: /dev/null
    type: disk
  aadisable2:
    path: /dev/zfs
    source: /dev/zfs
    type: disk

