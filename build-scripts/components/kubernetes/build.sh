#!/bin/bash -x

INSTALL="${1}"

DIR=`realpath $(dirname "${0}")`
GIT_TAG="$("${DIR}/version.sh")"

if [ ! -d "${SNAPCRAFT_PART_BUILD}/eks-distro" ]; then
  git clone --depth 1 https://github.com/aws/eks-distro $SNAPCRAFT_PART_BUILD/eks-distro
else
  (cd $SNAPCRAFT_PART_BUILD/eks-distro && git fetch --all && git pull)
fi

export EKS_TRACK=$(echo "$GIT_TAG" | cut -f1,2 -d'.' | tr -s . - | cut -c2-)
for patch in "${SNAPCRAFT_PART_BUILD}"/eks-distro/projects/kubernetes/kubernetes/"${EKS_TRACK}"/patches/*.patch
do
  echo "Applying patch $patch"
  git am < "$patch"
done

for app in kubectl kubelite; do
  if [ "$app" = "kubelite" ]
  then
    make WHAT="cmd/${app}" GOFLAGS=-tags=libsqlite3,dqlite CGO_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include/" CGO_LDFLAGS="-L${SNAPCRAFT_STAGE}/lib" CGO_LDFLAGS_ALLOW="-Wl,-z,now" KUBE_CGO_OVERRIDES=kubelite
  else
    make WHAT="cmd/${app}" KUBE_STATIC_OVERRIDES=kubelite
  fi
  cp _output/bin/"${app}" "${INSTALL}/${app}"
done

_output/bin/kubectl completion bash \
  | sed "s/complete -o default -F __start_kubectl kubectl/complete -o default -F __start_kubectl microk8s.kubectl/g" \
  | sed "s/complete -o default -o nospace -F __start_kubectl kubectl/complete -o default -o nospace -F __start_kubectl microk8s.kubectl/g" \
  > _output/kubectl.bash

cp _output/kubectl.bash "${INSTALL}/kubectl.bash"
