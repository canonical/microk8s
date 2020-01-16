import logging

import click

from cli.echo import Echo
from vm_providers.factory import get_provider_for
from vm_providers.errors import ProviderNotFound

logger = logging.getLogger(__name__)


@click.command(name="microk8s", context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
@click.option('-h', '--help', is_flag=True)
@click.pass_context
def cli(ctx, help):
    if help:
        show_help()

    if len(ctx.args) == 0:
        show_error()
        exit(1)

    if ctx.args[0] == 'install':
        install()
    elif ctx.args[0] == 'uninstall':
        uninstall()
    else:
        try:
            run(ctx.args)
        except Exception:
            show_error()


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
  install      Installs MicroK8s
  uninstall    Removes MicroK8s"""
    click.echo(msg)


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


def uninstall():
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


def update():
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
    except ProviderNotFound as provider_error:
        if provider_error.prompt_installable:
            if echo.is_tty_connected():
                echo.warning("MicroK8s is not running.")
            return 1
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    commands = instance._run("ls /snap/bin/ -1".split(), True)
    print(commands.decode("utf-8").split())


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
    instance._run(cmd)


if __name__ == '__main__':
    cli()
