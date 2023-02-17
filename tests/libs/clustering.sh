#!/usr/bin/env bash

function test_clustering() {
  # Test clustering. This test will create lxc containers or multipass VMs
  # therefore we do not need to run it inside a VM/container
  TRY_ATTEMPT=0
  while ! (timeout 3600 pytest -s tests/test-cluster.py) &&
        ! [ ${TRY_ATTEMPT} -eq 3 ]
  do
    TRY_ATTEMPT=$((TRY_ATTEMPT+1))
    sleep 1
  done
  if [ ${TRY_ATTEMPT} -eq 3 ]
  then
    echo "Test clusterring took longer than expected"
    exit 1
  fi
}