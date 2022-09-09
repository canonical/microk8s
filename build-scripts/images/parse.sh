#!/bin/bash -x

set -ex

GIT_TAG="$("$SNAPCRAFT_PROJECT_DIR/build-scripts/components/kubernetes/version.sh")"
INSTALL="${1}"

if [ ! -d "${SNAPCRAFT_PART_BUILD}/eks-distro" ]; then
  git clone --depth 1 https://github.com/aws/eks-distro "${SNAPCRAFT_PART_BUILD}/eks-distro"
else
  (cd "${SNAPCRAFT_PART_BUILD}/eks-distro" && git fetch --all && git pull)
fi

EKS_TRACK=$(echo "${GIT_TAG}" | cut -f1,2 -d'.' | tr -s . - | cut -c2-)
EKS_RELEASE=$(cat "${SNAPCRAFT_PART_BUILD}"/eks-distro/release/"${EKS_TRACK}"/production/RELEASE)

curl "https://distro.eks.amazonaws.com/kubernetes-$EKS_TRACK/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" -o "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml"

mkdir -p $INSTALL/etc
python3 parse.py "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" "$INSTALL/etc"
