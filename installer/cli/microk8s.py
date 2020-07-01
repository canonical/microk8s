import argparse
import logging
import traceback
from typing import List
from sys import exit, platform

import click

from cli.echo import Echo
from common.auxillary import Windows, MacOS
from common.errors import BaseError
from vm_providers.factory import get_provider_for
from vm_providers.errors import ProviderNotFound, ProviderInstanceNotFoundError
from common import definitions

logger = logging.getLogger(__name__)


@click.command(
    name="microk8s", context_settings=dict(ignore_unknown_options=True, allow_extra_args=True,)
)
@click.option("-h", "--help", is_flag=True)
@click.pass_context
def cli(ctx, help):
    try:
        if help and len(ctx.args) == 0:
            show_help()
            exit(0)
        elif help:
            ctx.args.append("--help")

        if len(ctx.args) == 0:
            show_error()
            exit(1)
        if ctx.args[0] == "install":
            install(ctx.args[1:])
            exit(0)
        elif ctx.args[0] == "uninstall":
            uninstall()
            exit(0)
        elif ctx.args[0] == "stop":
            run(ctx.args)
            stop()
            exit(0)
        elif ctx.args[0] == "dashboard-proxy":
            dashboard_proxy()
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
  install         Installs MicroK8s. Use --cpu, --mem, --disk and --channel to configure your setup.
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


def _show_install_help():
    msg = """Usage: microk8s install OPTIONS

    Options:
      --help     Show this message and exit.
      --cpu      Cores used by MicroK8s (default={})
      --mem      RAM in GB used by MicroK8s (default={})
      --disk     Maximum volume in GB of the dynamically expandable hard disk to be used (default={})
      --channel  Kubernetes version to install (default={})
       -y, --assume-yes  Automatic yes to prompts"""
    Echo.info(
        msg.format(
            definitions.DEFAULT_CORES,
            definitions.DEFAULT_MEMORY,
            definitions.DEFAULT_DISK,
            definitions.DEFAULT_CHANNEL,
        )
    )


def install(args) -> None:
    if "--help" in args or "-h" in args:
        _show_install_help()
        return
    parser = argparse.ArgumentParser("microk8s install")
    parser.add_argument("--cpu", default=definitions.DEFAULT_CORES, type=int)
    parser.add_argument("--mem", default=definitions.DEFAULT_MEMORY, type=int)
    parser.add_argument("--disk", default=definitions.DEFAULT_DISK, type=int)
    parser.add_argument("--channel", default=definitions.DEFAULT_CHANNEL, type=str)
    parser.add_argument(
        "-y", "--assume-yes", action="store_true", default=definitions.DEFAULT_ASSUME
    )
    args = parser.parse_args(args)

    echo = Echo()

    if platform == "win32":
        aux = Windows(args)
        if not aux.is_enough_space():
            echo.warning("VM disk size requested exceeds free space on host.")

    if platform == "darwin":
        aux = MacOS(args)
        if not aux.is_enough_space():
            echo.warning("VM disk size requested exceeds free space on host.")

    vm_provider_name: str = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    try:
        vm_provider_class.ensure_provider()
    except ProviderNotFound as provider_error:
        if provider_error.prompt_installable:
            if args.assume_yes or (
                echo.is_tty_connected()
                and echo.confirm(
                    "Support for {!r} needs to be set up. "
                    "Would you like to do that it now?".format(provider_error.provider)
                )
            ):
                vm_provider_class.setup_provider(echoer=echo)
            else:
                raise provider_error
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    instance.launch_instance(vars(args))
    echo.info("MicroK8s is up and running. See the available commands with `microk8s --help`.")


def uninstall() -> None:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
    except ProviderNotFound as provider_error:
        if provider_error.prompt_installable:
            if echo.is_tty_connected():
                echo.warning(
                    (
                        "MicroK8s is not running. VM provider {!r} has been removed.".format(
                            provider_error.provider
                        )
                    )
                )
            return 1
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    instance.destroy()
    echo.info("Thank you for using MicroK8s!")


def dashboard_proxy() -> None:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
        instance = vm_provider_class(echoer=echo)
        instance.get_instance_info()

        echo.info("Checking if Dashboard is running.")
        command = ["microk8s.enable", "dashboard"]
        output = instance.run(command, hide_output=True)
        if b"Addon dashboard is already enabled." not in output:
            echo.info("Waiting for Dashboard to come up.")
            command = [
                "microk8s.kubectl",
                "-n",
                "kube-system",
                "wait",
                "--timeout=240s",
                "deployment",
                "kubernetes-dashboard",
                "--for",
                "condition=available",
            ]
            instance.run(command, hide_output=True)

        command = ["microk8s.kubectl", "-n", "kube-system", "get", "secret"]
        output = instance.run(command, hide_output=True)
        secret_name = None
        for line in output.split(b"\n"):
            if line.startswith(b"default-token"):
                secret_name = line.split()[0].decode()
                break

        if not secret_name:
            echo.error("Cannot find the dashboard secret.")

        command = ["microk8s.kubectl", "-n", "kube-system", "describe", "secret", secret_name]
        output = instance.run(command, hide_output=True)
        token = None
        for line in output.split(b"\n"):
            if line.startswith(b"token:"):
                token = line.split()[1].decode()

        if not token:
            echo.error("Cannot find token from secret.")

        ip = instance.get_instance_info().ipv4[0]

        echo.info("Dashboard will be available at https://{}:10443".format(ip))
        echo.info("Use the following token to login:")
        echo.info(token)

        command = [
            "microk8s.kubectl",
            "port-forward",
            "-n",
            "kube-system",
            "service/kubernetes-dashboard",
            "10443:443",
            "--address",
            "0.0.0.0",
        ]

        try:
            instance.run(command)
        except KeyboardInterrupt:
            return
    except ProviderInstanceNotFoundError as provider_error:
        _not_installed(echo)
        return 1


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
        instance = vm_provider_class(echoer=echo)
        instance.get_instance_info()
        command = cmd[0]
        cmd[0] = "microk8s.{}".format(command)
        instance.run(cmd)
    except ProviderInstanceNotFoundError as provider_error:
        _not_installed(echo)
        return 1


def _not_installed(echo) -> None:
    if echo.is_tty_connected():
        echo.warning("MicroK8s is not installed. Please run `microk8s install`.")


def _get_microk8s_commands() -> List:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
        instance = vm_provider_class(echoer=echo)
        instance_info = instance.get_instance_info()
        if instance_info.is_running():
            commands = instance.run("ls -1 /snap/bin/".split(), hide_output=True)
            mk8s = [
                c.decode().replace("microk8s.", "")
                for c in commands.split()
                if c.decode().startswith("microk8s.")
            ]
            complete = mk8s
            if 'dashboard-proxy' not in mk8s:
                complete += ['dashboard-proxy']
            complete.sort()
            return complete
        else:
            return ["start", "stop"]
    except ProviderNotFound as provider_error:
        return ["start", "stop"]


if __name__ == "__main__":
    cli()
