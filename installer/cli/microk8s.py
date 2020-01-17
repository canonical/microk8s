import logging
import string
import traceback
from typing import List

import click

from cli.echo import Echo
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
        if help:
            show_help()
            exit(0)

        if len(ctx.args) == 0:
            show_error()
            exit(1)

        if ctx.args[0] == 'install':
            install()
        elif ctx.args[0] == 'uninstall':
            uninstall()
        else:
            run(ctx.args)
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
  install         Installs MicroK8s
  uninstall       Removes MicroK8s"""
    click.echo(msg)
    commands = _get_microk8s_commands()
    for command in commands:
        if command in definitions.command_descriptions:
            click.echo("  {:<15} {}".format(command, definitions.command_descriptions[command]))
        else:
            click.echo("  {:<15}".format(command))
    if len(commands) == 2:
        click.echo("")
        click.echo("Install and start MicroK8s to see the full list of commands.")


def install() -> None:
    vm_provider_name: str = 'multipass'
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
    except ProviderNotFound as provider_error:
        if provider_error.prompt_installable:
            if echo.is_tty_connected() and echo.confirm(
                "Support for {!r} needs to be set up. "
                "Would you like to do that it now?".format(provider_error.provider)
            ):
                vm_provider_class.setup_provider(echoer=echo)
            else:
                raise provider_error
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    instance.launch_instance()
    echo.info("MicroK8s is up and running. See the available commands with 'microk8s --help'.")


def uninstall() -> None:
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


def run(cmd):
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
    instance.launch_instance()
    command = cmd[0]
    cmd[0] = "microk8s.{}".format(command)
    instance.run(cmd)


def _get_microk8s_commands() -> List:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
        instance = vm_provider_class(echoer=echo)
        instance_info = instance.get_instance_info()
        if instance_info.is_running():
            commands = instance.run('ls -1 /snap/bin/'.split(), hide_output=True)
            mk8s = [c.decode().replace('microk8s.', '') for c in commands.split() if c.decode().startswith('microk8s')]
            return mk8s
        else:
            return ["start", "stop"]
    except ProviderNotFound as provider_error:
        return ["start", "stop"]


if __name__ == '__main__':
    cli()
