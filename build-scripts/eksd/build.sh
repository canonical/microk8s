#!/bin/bash -x

set -ex

source "$SNAPCRAFT_PROJECT_DIR/build-scripts/components/kubernetes/version.sh"
INSTALL="${1}"

if [ ! -d "${SNAPCRAFT_PART_BUILD}/eks-distro" ]; then
  git clone --depth 1 https://github.com/aws/eks-distro "${SNAPCRAFT_PART_BUILD}/eks-distro"
else
  (cd "${SNAPCRAFT_PART_BUILD}/eks-distro" && git fetch --all && git pull)
fi

EKS_RELEASE=$(cat "${SNAPCRAFT_PART_BUILD}"/eks-distro/release/"${EKS_TRACK}"/production/RELEASE)

# The version we want to set to the package should look something like v1.23-5
snapcraftctl set-version "v$KUBE_TRACK-$EKS_RELEASE"

curl "https://distro.eks.amazonaws.com/kubernetes-$EKS_TRACK/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" -o "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml"

mkdir -p $INSTALL/images
python3 parse-manifest.py "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" "$INSTALL/images"
