#!/bin/bash -x

# List of addon repositories to bundle in the snap
# (name),(repository),(reference)
ADDONS_REPOS="
core,https://github.com/canonical/microk8s-core-addons,1.25-eksd
community,https://github.com/canonical/microk8s-community-addons,1.25-eksd
eksd,https://github.com/canonical/microk8s-aws-addons,1.25-eksd
"

# List of addon repositories to automatically enable
ADDONS_REPOS_ENABLED="core eksd"

INSTALL="${1}"
if [ -d "${INSTALL}/addons" ]; then
  rm -rf "${INSTALL}/addons"
fi
if [ -d addons ]; then
  rm -rf addons
fi

IFS=';'
echo "${ADDONS_REPOS}" | while read line; do
  if [ -z "${line}" ];
    then continue
  fi
  name="$(echo ${line} | cut -f1 -d',')"
  repository="$(echo ${line} | cut -f2 -d',')"
  reference="$(echo ${line} | cut -f3 -d',')"
  git clone "${repository}" -b "${reference}" "addons/${name}"
done
echo "${ADDONS_REPOS_ENABLED}" > addons/.auto-add

cp -r "addons" "${INSTALL}/addons"
