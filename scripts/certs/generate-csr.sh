#!/usr/bin/env bash -e

########################################################################
# Description:
#   Generate CSR for component certificates. The CSR PEM is written to stdout. Arguments are:
#   1. The certificate subject, e.g. "/CN=system:kube-scheduler"
#   2. The path to write the private key, e.g. "$SNAP_DATA/certs/scheduler.key"
#
# Example usage:
#   $SNAP/scripts/certs/generate-csr.sh /CN=system:kube-scheduler $SNAP_DATA/certs/scheduler.key > $SNAP_DATA/certs/scheduler.csr
########################################################################

OPENSSL=openssl

# generate key if it does not exist
if [ ! -f "$2" ]; then
  "${OPENSSL}" genrsa 2048 -out "$2"
  chown 0:0 "$2" || true
  chmod 0600 "$2" || true
fi

# generate csr
"${OPENSSL}" req -new -sha256 -subj "$1" -key "$2"
