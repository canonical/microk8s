#!/usr/bin/env bash

source tests/libs/utils.sh
source tests/libs/clustering.sh
source tests/libs/addons-upgrade.sh
source tests/libs/upgrade-path.sh
source tests/libs/addons.sh

if echo "$*" | grep -q -- 'help'; then
    prog=$(basename -s.wrapper "$0")
    echo "Usage: $prog LXC-IMAGE ORIGINAL-CHANNEL UPGRADE-WITH-CHANNEL [PROXY]"
    echo ""
    echo "Example: $prog ubuntu:18.04 latest/beta latest/edge"
    echo "Use Ubuntu 18.04 for running our tests."
    echo "We test that microk8s from latest/edge (UPGRADE-WITH-CHANNEL) runs fine."
    echo "We test that microk8s from latest/beta (ORIGINAL-CHANNEL) can be upgraded"
    echo "to the revision that is currently on latest/edge (UPGRADE-WITH-CHANNEL)."
    echo
    exit
fi

set -uex

setup_tests "$@"

DISABLE_AIRGAP_TESTS="${DISABLE_AIRGAP_TESTS:-0}"
if [ "x${DISABLE_AIRGAP_TESTS}" != "x1" ]; then
  . tests/test-airgap.sh
fi

test_clustering

setup_addons_upgrade
test_addons_upgrade
post_addons_upgrade

setup_upgrade_path
test_upgrade_path
post_upgrade_path

setup_test_addons
test_smoke
test_core_addons
test_community_addons
test_eksd_addons
test_gpu_addon
post_test_addons
