#!/usr/bin/env python3

import click

from common.utils import ensure_started, exit_if_no_permission, is_cluster_locked, xable
from status import get_status, get_available_addons, get_current_arch


@click.command(context_settings={'ignore_unknown_options': True})
@click.argument('addons', nargs=-1, required=True)
def disable(addons):
    """Disables one or more MicroK8s addons.

    For a list of available addons, run `microk8s status`.

    To see help for individual addons, run:

        microk8s disable ADDON -- --help
    """

    is_cluster_locked()
    exit_if_no_permission()
    ensure_started()

    _, disabled_addons = get_status(get_available_addons(get_current_arch()), True)
    disabled_addons = {a['name'] for a in disabled_addons}

    xable('disable', addons, disabled_addons)


if __name__ == '__main__':
    disable(prog_name='microk8s disable')
