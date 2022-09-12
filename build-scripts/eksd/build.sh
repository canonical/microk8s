#!/bin/bash -x

set -ex

source "$SNAPCRAFT_PROJECT_DIR/build-scripts/components/kubernetes/version.sh"
INSTALL="${1}"
EKS_RELEASE="$(curl -L --silent "https://raw.githubusercontent.com/aws/eks-distro/main/release/"${EKS_TRACK}"/production/RELEASE")"

# The version we want to set to the package should look something like v1.23-5
snapcraftctl set-version "v$KUBE_TRACK-$EKS_RELEASE"

curl "https://distro.eks.amazonaws.com/kubernetes-$EKS_TRACK/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" -o "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml"

mkdir -p $INSTALL/images
python3 parse-manifest.py "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" "$INSTALL/images"
