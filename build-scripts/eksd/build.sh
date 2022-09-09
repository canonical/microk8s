#!/bin/bash -x

set -ex

source "$SNAPCRAFT_PROJECT_DIR/build-scripts/components/kubernetes/version.sh"
INSTALL="${1}"

if [ ! -d "${SNAPCRAFT_PART_BUILD}/eks-distro" ]; then
  git clone --depth 1 https://github.com/aws/eks-distro "${SNAPCRAFT_PART_BUILD}/eks-distro"
else
  (cd "${SNAPCRAFT_PART_BUILD}/eks-distro" && git fetch --all && git pull)
fi

EKS_TRACK=$(echo "${KUBE_TRACK}" | cut -f1,2 -d'.' | tr -s . -)
EKS_RELEASE=$(cat "${SNAPCRAFT_PART_BUILD}"/eks-distro/release/"${EKS_TRACK}"/production/RELEASE)

snapcraftctl set-version "$KUBE_TRACK.$EKS_RELEASE"

curl "https://distro.eks.amazonaws.com/kubernetes-$EKS_TRACK/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" -o "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml"

mkdir -p $INSTALL/images
python3 parse-manifest.py "${SNAPCRAFT_PART_BUILD}/kubernetes-$EKS_TRACK-eks-$EKS_RELEASE.yaml" "$INSTALL/images"

export KUBE_VERSION=$(cat "$SNAPCRAFT_PART_BUILD/eksd-components/kubernetes/git-tag")
cat "$SNAPCRAFT_PART_BUILD/eksd-components/kubernetes/git-tag" > $SNAPCRAFT_STAGE/KUBE_VERSION
