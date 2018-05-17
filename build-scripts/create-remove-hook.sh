#!/bin/sh
set -eu

mkdir -p meta/hooks

cat << 'EOF' > meta/hooks/remove
#!/bin/bash
set -eu

#TODO(kjackal): Make sure this works everywhere we want
if [ -f /etc/apparmor.d/docker ]; then
  echo "Updating docker-default profile"
  gawk -i inplace '!/^  signal \(receive\) peer=snap.microk8s.daemon-docker,$/ {print}' /etc/apparmor.d/docker
  echo "Reloading AppArmor profiles"
  service apparmor reload
  echo "AppArmor patched"
fi

EOF

chmod +x meta/hooks/remove
