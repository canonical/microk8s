#!/usr/bin/env python3

"""
Migrate old worker node traefik configs to new proxy format.
"""

import json
import os
from pathlib import Path

import yaml

is_worker = Path(os.path.expandvars("$SNAP_DATA/var/lock/clustered.lock"))
traefik_config_file = Path(os.path.expandvars("$SNAP_DATA/args/traefik/traefik.yaml"))
provider_config_file = Path(os.path.expandvars("$SNAP_DATA/args/traefik/provider.yaml"))
proxy_config_file = Path(os.path.expandvars("$SNAP_DATA/args/apiserver-proxy-config"))


def main():
    if any(not f.exists() for f in [is_worker, traefik_config_file, provider_config_file]):
        return

    try:
        traefik_config = yaml.load(traefik_config_file.read_bytes())
        listen = traefik_config["entrypoints"]["apiserver"]["address"]
    except (yaml.error.YAMLError, OSError, KeyError):
        listen = "127.0.0.1:16443"

    try:
        provider_config = yaml.load(provider_config_file.read_bytes())
        endpoints = provider_config["tcp"]["services"]["kube-apiserver"]["loadBalancer"]["servers"]
        if not endpoints:
            return
    except (yaml.error.YAMLError, OSError, KeyError):
        return

    proxy_config_file.write_text(
        json.dumps({"listen": listen, "endpoints": [e["address"] for e in endpoints]})
    )

    # delete old configuration files
    provider_config_file.unlink()
    traefik_config_file.unlink()


if __name__ == "__main__":
    main()
