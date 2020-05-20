#!/usr/bin/env bash

set -e

source $SNAP/actions/common/utils.sh

echo "Enabling Kubernetes Dashboard"
"$SNAP/microk8s-enable.wrapper" metrics-server
echo "Applying manifest"
use_manifest dashboard apply

echo "
If RBAC is not enabled access the dashboard using the default token retrieved with:

token=\$(microk8s kubectl -n kube-system get secret | grep default-token | cut -d \" \" -f1)
microk8s kubectl -n kube-system describe secret \$token

In an RBAC enabled setup (microk8s enable RBAC) you need to create a user with restricted
permissions as shown in:
https://github.com/kubernetes/dashboard/blob/master/docs/user/access-control/creating-sample-user.md
"

