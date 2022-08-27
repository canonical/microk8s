#!/bin/bash

> "${SNAP_DIR}"/.workload_endpoints

for podnamespace in \
  $(microk8s kubectl get po -A -o \
  jsonpath="{range .items[*]}{.metadata.namespace}{'.'}{.metadata.name}{'\n'}{end}")
do
  digest=$(echo -n $podnamespace | sha1sum | cut -b -11)
  echo "cali${digest}" >> "${SNAP_DIR}"/.workload_endpoints
done
