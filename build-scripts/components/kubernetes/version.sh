#!/bin/bash

KUBE_TRACK="${KUBE_TRACK:-1.22}"            # example: "1.24"
KUBE_VERSION="${KUBE_VERSION:-}"        # example: "v1.24.2"
EKS_TRACK=$(echo "${KUBE_TRACK}" | cut -f1,2 -d'.' | tr -s . -) # example: "1-24"

if [ -z "${KUBE_VERSION}" ]; then
  KUBE_VERSION=$(curl -L --silent https://raw.githubusercontent.com/aws/eks-distro/main/projects/kubernetes/kubernetes/${EKS_TRACK}/GIT_TAG)
fi

echo "${KUBE_VERSION}"
