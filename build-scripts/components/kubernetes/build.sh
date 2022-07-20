#!/bin/bash -x

INSTALL="${1}"

for app in kubelite kubectl; do
  if [ "$app" == "kubelite" ]; then
    make WHAT="cmd/${app}" GOFLAGS=-tags=libsqlite3,dqlite CGO_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include/" CGO_LDFLAGS="-L${SNAPCRAFT_STAGE}/lib" CGO_LDFLAGS_ALLOW="-Wl,-z,now" KUBE_CGO_OVERRIDES=kubelite
  else
    make WHAT="cmd/${app}"
  fi
  cp _output/bin/"${app}" "${INSTALL}/${app}"
done

_output/bin/kubectl completion bash \
  | sed "s/complete -o default -F __start_kubectl kubectl/complete -o default -F __start_kubectl microk8s.kubectl/g" \
  | sed "s/complete -o default -o nospace -F __start_kubectl kubectl/complete -o default -o nospace -F __start_kubectl microk8s.kubectl/g" \
  > _output/kubectl.bash

cp _output/kubectl.bash "${INSTALL}/kubectl.bash"
