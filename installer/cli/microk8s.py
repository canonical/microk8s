import os
import argparse
import logging
import traceback
from typing import List
from sys import exit, platform

import click

from cli.echo import Echo
from cli.checkpoint import sync, get_microk8s_commands, ALIAS_PATH
from common.errors import BaseError
from vm_providers.factory import get_provider_for
from vm_providers.errors import ProviderNotFound
from common import definitions

logger = logging.getLogger(__name__)


@click.command(name="microk8s", context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
@click.option('-h', '--help', is_flag=True)
@click.pass_context
def cli(ctx, help):
    try:
        sync()
        if help and len(ctx.args) == 0:
            show_help()
            exit(0)
        elif help:
            ctx.args.append("--help")

        if len(ctx.args) == 0:
            show_error()
            exit(1)
        if ctx.args[0] == 'install':
            install(ctx.args[1:])
            exit(0)
        elif ctx.args[0] == 'uninstall':
            uninstall()
            exit(0)
        elif ctx.args[0] == 'stop':
            run(ctx.args)
            stop()
            exit(0)
        elif ctx.args[0] == 'sync':
            sync(force=True)
            exit(0)
        else:
            run(ctx.args)
            exit(0)

    except BaseError as e:
        Echo.error(str(e))
        exit(e.get_exit_code())
    except Exception as e:
        Echo.error("An unexpected error occurred.")
        Echo.info(str(e))
        Echo.info(traceback.print_exc())
        exit(254)


def show_error():
    msg = """Usage: microk8s [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Shows the available COMMANDS."""
    click.echo(msg)


def show_help():
    msg = """Usage: microk8s [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  install         Installs MicroK8s. Use --cpu, --mem, --disk to appoint resources.
  uninstall       Removes MicroK8s"""
    click.echo(msg)
    commands = get_microk8s_commands()
    for command in commands:
        if command in definitions.command_descriptions:
            click.echo("  {:<15} {}".format(command, definitions.command_descriptions[command]))
        else:
            click.echo("  {:<15}".format(command))
    if len(commands) == 2:
        click.echo("")
        click.echo("Install and start MicroK8s to see the full list of commands.")


def _show_install_help():
    msg = """Usage: microk8s install OPTIONS

    Options:
      --help  Show this message and exit.
      --cpu   Cores used by MicroK8s (default={})
      --mem   RAM in GB used by MicroK8s (default={})
      --disk  Maximum volume in GB of the dynamicaly expandable hard disk to be used (default={})
       -y, --assume-yes  Automatic yes to prompts"""
    Echo.info(msg.format(definitions.DEFAULT_CORES, definitions.DEFAULT_MEMORY, definitions.DEFAULT_DISK))


def install(args) -> None:
    if "--help" in args:
        _show_install_help()
        return

    if platform in ['linux', 'darwin']:
        bashrc = os.path.join(os.path.expanduser('~'), '.bashrc')
        zshenv = os.path.join(os.path.expanduser('~'), '.zshenv')
        for shell_file in [bashrc, zshenv]:
            if os.path.isfile(shell_file):
                with open(shell_file, 'a') as f:
                    f.writelines([
                        '',
                        '# Added by MicroK8s installer.',
                        'if test -f {}; then'.format(ALIAS_PATH),
                        '    source {}'.format(ALIAS_PATH),
                        'fi'
                    ])

    elif platform in ['win32']:
        pass  # TODO: Set Windows registry to source this file: https://superuser.com/questions/144347/is-there-windows-equivalent-to-the-bashrc-file-in-linux


    parser = argparse.ArgumentParser("microk8s install")
    parser.add_argument('--cpu', default=definitions.DEFAULT_CORES, type=int)
    parser.add_argument('--mem', default=definitions.DEFAULT_MEMORY, type=int)
    parser.add_argument('--disk', default=definitions.DEFAULT_DISK, type=int)
    parser.add_argument('-y', '--assume-yes', action='store_true', default=definitions.DEFAULT_ASSUME)
    args = parser.parse_args(args)
    vm_provider_name: str = 'multipass'
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
    except ProviderNotFound as provider_error:
        if provider_error.prompt_installable:
            if echo.is_tty_connected() and args.assume_yes:
                vm_provider_class.setup_provider(echoer=echo)
            elif echo.is_tty_connected() and echo.confirm(
                "Support for {!r} needs to be set up. "
                "Would you like to do that it now?".format(provider_error.provider)
            ) and not args.assume_yes:
                vm_provider_class.setup_provider(echoer=echo)
            else:
                raise provider_error
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    instance.launch_instance(vars(args))
    echo.info("MicroK8s is up and running. See the available commands with 'microk8s --help'.")


def uninstall() -> None:
    # TODO: Remove source / regkey.

    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
    except ProviderNotFound as provider_error:
        if provider_error.prompt_installable:
            if echo.is_tty_connected():
                echo.warning((
                    "MicroK8s is not running. VM provider {!r} has been removed."
                    .format(provider_error.provider)))
            return 1
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    instance.destroy()
    echo.info("Thank you for using MicroK8s!")


def stop() -> None:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    vm_provider_class.ensure_provider()
    instance = vm_provider_class(echoer=Echo())
    instance_info = instance.get_instance_info()
    if instance_info.is_running():
        instance.stop()


def run(cmd) -> None:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
    except ProviderNotFound as provider_error:
        if provider_error.prompt_installable:
            if echo.is_tty_connected():
                echo.warning("MicroK8s is not installed. Please run 'microk8s install'.")
            return 1
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    command = cmd[0]
    cmd[0] = "microk8s.{}".format(command)
    instance.run(cmd)


if __name__ == '__main__':
    cli()
