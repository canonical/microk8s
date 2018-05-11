
#!/bin/bash

set -eux

sleep 30
n=0
until [ $n -ge 10 ]
do
  (/snap/bin/microk8s.kubectl get all --all-namespaces | grep -z "service/kubernetes") && exit 0
  n=$[$n+1]
  sleep 20
done
exit 1
