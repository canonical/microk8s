#!/usr/bin/env bash -e

########################################################################
# Description:
#   Generate CSR for component certificates, including hostname and node IP addresses
#   as SubjectAlternateNames. The CSR PEM is printed to stdout. Arguments are:
#   1. The certificate subject, e.g. "/CN=system:node:$hostname/O=system:nodes"
#   2. The path to write the private key, e.g. "$SNAP_DATA/certs/kubelet.key"
#
# Notes:
#   - Subject is /CN=system:node:$hostname/O=system:nodes
#   - Node hostname and IP addresses are added as Subject Alternate Names
#
# Example usage:
#   $SNAP/scripts/certs/generate-csr-with-sans.sh /CN=system:node:$hostname/O=system:nodes $SNAP_DATA/certs/kubelet.key > $SNAP_DATA/certs/kubelet.csr
########################################################################

OPENSSL=openssl

# "get_ips"
. $SNAP/actions/common/utils.sh

# Add DNS name and IP addresses as subjectAltName
hostname=$(hostname | tr '[:upper:]' '[:lower:]')
subjectAltName="DNS:$hostname"
for ip in $(get_ips); do
  subjectAltName="$subjectAltName, IP:$ip"
done

# generate key if it does not exist
if [ ! -f "$2" ]; then
  "${OPENSSL}" genrsa 2048 -out "$2"
  chown 0:0 "$2" || true
  chmod 0600 "$2" || true
fi

# generate csr
"${OPENSSL}" req -new -sha256 -subj "$1" -key "$2" -addext "subjectAltName = $subjectAltName"
