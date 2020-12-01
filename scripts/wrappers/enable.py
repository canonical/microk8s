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
from status import get_available_addons, get_current_arch, get_status


@click.command(context_settings={'ignore_unknown_options': True})
@click.argument('addons', nargs=-1, required=True)
def enable(addons):
    """Enables a MicroK8s addon.

    For a list of available addons, run `microk8s status`.

    To see help for individual addons, run:

        microk8s enable ADDON -- --help
    """

    if check_help_flag(addons):
        return

    is_cluster_locked()
    exit_if_no_permission()
    ensure_started()
    wait_for_ready(timeout=30)

    enabled_addons, _ = get_status(get_available_addons(get_current_arch()), True)
    enabled_addons = {a['name'] for a in enabled_addons}

    xable('enable', addons, enabled_addons)


if __name__ == '__main__':
    enable(prog_name='microk8s enable')
