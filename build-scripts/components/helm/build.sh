#!/bin/bash

INSTALL="${1}"
mkdir -p "${INSTALL}/bin"

make
cp bin/helm "${INSTALL}/bin/helm"

./bin/helm completion bash \
  | sed "s/complete -o default -F __start_helm helm/complete -o default -F __start_helm microk8s.helm/g" \
  | sed "s/complete -o default -o nospace -F __start_helm helm/complete -o default -o nospace -F __start_helm microk8s.helm/g" \
  > helm.bash

./bin/helm completion bash \
  | sed "s/complete -o default -F __start_helm helm/complete -o default -F __start_helm microk8s.helm3/g" \
  | sed "s/complete -o default -o nospace -F __start_helm helm/complete -o default -o nospace -F __start_helm microk8s.helm3/g" \
  > helm3.bash

cp helm.bash "${INSTALL}/helm.bash"
cp helm3.bash "${INSTALL}/helm3.bash"
