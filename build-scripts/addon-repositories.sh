#!/bin/bash

ADDONS_REPOS="
core,${CORE_ADDONS_REPO:-https://github.com/canonical/microk8s-core-addons},${CORE_ADDONS_REPO_BRANCH:-main}
community,${COMMUNITY_ADDONS_REPO:-https://github.com/canonical/microk8s-community-addons},${COMMUNITY_ADDONS_REPO_BRANCH:-main}
"
ADDONS_REPOS_ENABLED="core"
