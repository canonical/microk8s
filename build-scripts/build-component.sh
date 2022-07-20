#!/bin/bash

set -ex

DIR=`realpath $(dirname "${0}")`

BUILD_DIRECTORY="${SNAPCRAFT_PART_BUILD:-${DIR}/.build}"
INSTALL_DIRECTORY="${SNAPCRAFT_PART_INSTALL:-${DIR}/.install}"

STRICT="${STRICT:-false}"
if [ "x${STRICT}" == "xfalse" ]; then
  PROJECT_DIR="${SNAPCRAFT_PROJECT_DIR:-${DIR}/..}"
  if cat "${PROJECT_DIR}/snap/snapcraft.yaml" | grep "confinement:" | grep strict > /dev/null; then
    STRICT="true"
  fi
fi

mkdir -p "${BUILD_DIRECTORY}" "${INSTALL_DIRECTORY}"

COMPONENT_NAME="${1}"
COMPONENT_DIRECTORY="${DIR}/components/${COMPONENT_NAME}"

GIT_REPOSITORY="$(cat "${COMPONENT_DIRECTORY}/repository")"
GIT_TAG="$("${COMPONENT_DIRECTORY}/version.sh")"

COMPONENT_BUILD_DIRECTORY="${BUILD_DIRECTORY}/${COMPONENT_NAME}"
if [ ! -d "${COMPONENT_BUILD_DIRECTORY}" ]; then
  git clone "${GIT_REPOSITORY}" --depth 1 -b "${GIT_TAG}" "${COMPONENT_BUILD_DIRECTORY}"
else
  cd "${COMPONENT_BUILD_DIRECTORY}"
  git checkout "${GIT_TAG}"
fi

cd "${COMPONENT_BUILD_DIRECTORY}"
git config user.name "MicroK8s builder bot"
git config user.email "microk8s-builder-bot@canonical.com"
if echo "${VERSION}" | grep -e rc -e alpha -e beta; then
  if [ -d "${COMPONENT_DIRECTORY}/pre-patches" ]; then
    for patch in "${COMPONENT_DIRECTORY}"/pre-patches/*; do
      git am < "${patch}"
    done
  fi
else
  if [ -d "${COMPONENT_DIRECTORY}/patches" ]; then
    for patch in "${COMPONENT_DIRECTORY}"/patches/*; do
      git am < "${patch}"
    done
  fi
fi
if [ "x${STRICT}" == "xtrue" ] && [ -d "${COMPONENT_DIRECTORY}/strict-patches" ]; then
    for patch in "${COMPONENT_DIRECTORY}"/strict-patches/*; do
      git am < "${patch}"
    done
fi

bash -xe "${COMPONENT_DIRECTORY}/build.sh" "${INSTALL_DIRECTORY}"
