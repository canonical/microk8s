#!/usr/bin/env python3

import click

from common.utils import (
    ensure_started,
    exit_if_no_permission,
    is_cluster_locked,
    check_help_flag,
    wait_for_ready,
    xable,
)


@click.command(
    context_settings={"ignore_unknown_options": True, "help_option_names": ["-h", "--help"]},
)
@click.argument("addons", nargs=-1, required=True)
def enable(addons) -> None:
    """
    Enable a MicroK8s addon.

    For a list of available addons, run `microk8s status`.

    To see help for individual addons, run:

        microk8s enable ADDON -- --help
    """
    if check_help_flag(addons):
        return

    is_cluster_locked()
    exit_if_no_permission()
    ensure_started()
    wait_for_ready(timeout=30, with_ready_node=False)

    xable("enable", addons)


if __name__ == "__main__":
    enable(prog_name="microk8s enable")
