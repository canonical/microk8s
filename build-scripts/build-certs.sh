#!/usr/bin/env bash

set -eu

mkdir certs
openssl genrsa -sha256 -out ./certs/serviceaccount.key 2048
openssl genrsa -sha256 -out ./certs/ca.key 2048
openssl req -x509 -new -sha256 -nodes -key ./certs/ca.key -subj "/C=GB/ST=Canonical/L=Canonical/O=Canonical/OU=Canonical/CN=127.0.0.1" -out ./certs/ca.crt
openssl req -x509 -new -sha256 -nodes -key ./certs/ca.key -out ./certs/ca.crt
openssl genrsa -sha256 -out ./certs/server.key 2048
openssl req -new -sha256 -key ./certs/server.key -out ./certs/server.csr -config $KUBE_SNAP_ROOT/microk8s-resources/certs/csr.conf -subj "/C=GB/ST=Canonical/L=Canonical/O=Canonical/OU=Canonical/CN=127.0.0.1"
openssl x509 -req -sha256 -in ./certs/server.csr -CA ./certs/ca.crt -CAkey ./certs/ca.key -CAcreateserial -out ./certs/server.crt -days 365 -extensions v3_ext -extfile $KUBE_SNAP_ROOT/microk8s-resources/certs/csr.conf
rm -rf .srl
