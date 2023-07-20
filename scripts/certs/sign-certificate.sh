#!/usr/bin/env bash -e

########################################################################
# Description:
#   Sign a certificate signing request (CSR) using the MicroK8s cluster CA.
#   The CSR is read through stdin, and the signed certificate is printed to stdout.
#
# Notes:
#   - Read from stdin and write to stdout, so no temporary files are required.
#   - Any SubjectAlternateNames that are included in the CSR are added to the certificate.
#
# Example usage:
#   cat component.csr | $SNAP/scripts/certs/sign-certificate.sh > component.crt
########################################################################

OPENSSL=openssl

# We need to use the request more than once, so read it into a variable
csr="$(cat)"

# Parse SANs from the CSR and add them to the certificate extensions (if any)
extensions=""
alt_names="$(echo "$csr" | "${OPENSSL}" req -text | grep "X509v3 Subject Alternative Name:" -A1 | tail -n 1 | sed 's,IP Address:,IP:,g')"
if test "x$alt_names" != "x"; then
  extensions="subjectAltName = $alt_names"
fi

# Sign certificate and print to stdout
echo "$csr" | "${OPENSSL}" x509 -req -sha256 -CA "${SNAP_DATA}/certs/ca.crt" -CAkey "${SNAP_DATA}/certs/ca.key" -CAcreateserial -days 3650 -extfile <(echo "${extensions}")
