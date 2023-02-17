#!/usr/bin/env bash

source tests/libs/airgap.sh

# test-airgap.sh is called from test-distro.sh

echo "1/7 -- Install registry mirror"
setup_airgap_registry_mirror
echo "2/7 -- Install MicroK8s addons"
setup_airgap_registry_addons
echo "3/7 -- Wait for MicroK8s instance to come up"
wait_airgap_registry
echo "4/7 -- Push images to registry mirror"
push_images_to_registry
echo "5/7 -- Install MicroK8s on an airgap environment"
setup_airgapped_microk8s
echo "6/7 -- Configure MicroK8s registry mirrors"
configure_airgapped_microk8s_mirrors
echo "7/7 -- Wait for airgap MicroK8s to come up"
test_airgapped_microk8s
echo "Cleaning up"
post_airgap_tests