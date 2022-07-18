#!/bin/bash -x

INSTALL="${1}"

for app in kubelite kubectl; do
  make WHAT="cmd/${app}"
  cp _output/bin/"${app}" "${INSTALL}/${app}"
done

_output/bin/kubectl completion bash \
  | sed "s/complete -o default -F __start_kubectl kubectl/complete -o default -F __start_kubectl microk8s.kubectl/g" \
  | sed "s/complete -o default -o nospace -F __start_kubectl kubectl/complete -o default -o nospace -F __start_kubectl microk8s.kubectl/g" \
  > _output/kubectl.bash

cp _output/kubectl.bash "${INSTALL}/kubectl.bash"
