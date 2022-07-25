#!/bin/bash

VERSION="${2}"

INSTALL="${1}"
mkdir -p "${INSTALL}/bin"

make VERSION="${VERSION}"
cp bin/helm "${INSTALL}/bin/helm"

./bin/helm completion bash \
  | sed "s/complete -o default -F __start_helm helm/complete -o default -F __start_helm microk8s.helm/g" \
  | sed "s/complete -o default -o nospace -F __start_helm helm/complete -o default -o nospace -F __start_helm microk8s.helm/g" \
  > bin/helm.bash

./bin/helm completion bash \
  | sed "s/complete -o default -F __start_helm helm/complete -o default -F __start_helm microk8s.helm3/g" \
  | sed "s/complete -o default -o nospace -F __start_helm helm/complete -o default -o nospace -F __start_helm microk8s.helm3/g" \
  > bin/helm3.bash

cp bin/helm.bash "${INSTALL}/helm.bash"
cp bin/helm3.bash "${INSTALL}/helm3.bash"
