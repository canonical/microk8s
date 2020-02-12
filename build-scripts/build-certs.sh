#!/usr/bin/env bash

set -eux

mkdir certs
openssl genrsa -out ./certs/serviceaccount.key 2048
openssl genrsa -out ./certs/ca.key 2048
openssl req -x509 -new -nodes -key ./certs/ca.key -subj "/CN=127.0.0.1" -days 10000 -out ./certs/ca.crt
openssl genrsa -out ./certs/server.key 2048
openssl req -new -key ./certs/server.key -out ./certs/server.csr -config $KUBE_SNAP_ROOT/microk8s-resources/certs/csr.conf
openssl x509 -req -in ./certs/server.csr -CA ./certs/ca.crt -CAkey ./certs/ca.key -CAcreateserial -out ./certs/server.crt -days 100000 -extensions v3_ext -extfile $KUBE_SNAP_ROOT/microk8s-resources/certs/csr.conf
rm -rf .srl
