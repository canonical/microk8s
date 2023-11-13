import argparse
import logging
import traceback
from typing import List
from sys import exit, platform
from os import getcwd

import click

from cli.echo import Echo
from common import definitions
from common.auxiliary import Windows, MacOS, Linux
from common.errors import BaseError
from common.file_utils import get_kubeconfig_path, clear_kubeconfig
from vm_providers.factory import get_provider_for
from vm_providers.errors import ProviderNotFound, ProviderInstanceNotFoundError

logger = logging.getLogger(__name__)


@click.command(
    name="microk8s",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
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
        elif ctx.args[0] == "start":
            start()
            run(ctx.args)
            exit(0)
        elif ctx.args[0] == "stop":
            run(ctx.args)
            stop()
            exit(0)
        elif ctx.args[0] == "kubectl":
            exit(kubectl(ctx.args[1:]))
        elif ctx.args[0] == "dashboard-proxy":
            dashboard_proxy()
            exit(0)
        elif ctx.args[0] == "inspect":
            inspect()
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
  install         Installs MicroK8s. Use --cpu, --mem, --disk, --channel, and --image to configure your setup.
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
    msg = f"""Usage: microk8s install OPTIONS

    Options:
      --help     Show this message and exit.
      --cpu      Cores used by MicroK8s (default={definitions.DEFAULT_CORES}, min={definitions.MIN_CORES})
      --mem      RAM in GB used by MicroK8s (default={definitions.DEFAULT_MEMORY_GB}, min={definitions.MIN_MEMORY_GB})
      --disk     Max volume in GB of the dynamically expandable hard disk to be used (default={definitions.DEFAULT_DISK_GB}, min={definitions.MIN_DISK_GB})
      --channel  Kubernetes version to install (default={definitions.DEFAULT_CHANNEL})
      --image    Ubuntu version to install (default={definitions.DEFAULT_IMAGE})
      -y, --assume-yes  Automatic yes to prompts"""  # noqa
    Echo.info(msg)


def memory(mem_gb: str) -> int:
    """
    Validates the value in --mem parameter of the install command.
    """
    mem_gb = int(mem_gb)
    if mem_gb < definitions.MIN_MEMORY_GB:
        raise ValueError("Out of valid memory range")
    return mem_gb


def cpu(cpus: str) -> int:
    """
    Validates the value in --cpu parameter of the install command.
    """
    cpus = int(cpus)
    if cpus < definitions.MIN_CORES:
        raise ValueError("Invalid number of cpus")
    return cpus


def disk(disk_gb: str) -> int:
    """
    Validates the value in --disk parameter of the install command.
    """
    disk_gb = int(disk_gb)
    if disk_gb < definitions.MIN_DISK_GB:
        raise ValueError("Out of valid disk range")
    return disk_gb


def install(args) -> None:
    if "--help" in args or "-h" in args:
        _show_install_help()
        return

    parser = argparse.ArgumentParser("microk8s install")
    parser.add_argument("--cpu", default=definitions.DEFAULT_CORES, type=cpu)
    parser.add_argument("--mem", default=definitions.DEFAULT_MEMORY_GB, type=memory)
    parser.add_argument("--disk", default=definitions.DEFAULT_DISK_GB, type=disk)
    parser.add_argument("--channel", default=definitions.DEFAULT_CHANNEL, type=str)
    parser.add_argument("--image", default=definitions.DEFAULT_IMAGE, type=str)
    parser.add_argument(
        "-y", "--assume-yes", action="store_true", default=definitions.DEFAULT_ASSUME
    )
    args = parser.parse_args(args)

    echo = Echo()

    if platform == "win32":
        host = Windows(args)
    elif platform == "darwin":
        host = MacOS(args)
    else:
        host = Linux(args)

    if not host.has_enough_cpus():
        echo.error("VM cpus requested exceed number of available cores on host.")
        exit(1)
    if not host.has_enough_memory():
        echo.warning("VM memory requested exceeds the total memory on host.")
        exit(1)
    if not host.has_enough_disk_space():
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
                    "Would you like to do that now?".format(provider_error.provider)
                )
            ):
                vm_provider_class.setup_provider(echoer=echo)
            else:
                raise provider_error
        else:
            raise provider_error

    instance = vm_provider_class(echoer=echo)
    spec = vars(args)
    spec.update({"kubeconfig": get_kubeconfig_path()})
    instance.launch_instance(spec)
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
    clear_kubeconfig()
    echo.info("Thank you for using MicroK8s!")


def kubectl(args) -> int:
    if platform == "win32":
        return Windows(args).kubectl()
    if platform == "darwin":
        return MacOS(args).kubectl()
    else:
        return Linux(args).kubectl()


def inspect() -> None:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
        instance = vm_provider_class(echoer=echo)
        instance.get_instance_info()

        command = ["microk8s.inspect"]
        output = instance.run(command, hide_output=True)
        tarball_location = None
        host_destination = getcwd()
        if b"Report tarball is at" not in output:
            echo.error("Report tarball not generated")
        else:
            for line_out in output.split(b"\n"):
                line_out = line_out.decode()
                line = line_out.strip()
                if line.startswith("Report tarball is at "):
                    tarball_location = line.split("Report tarball is at ")[1]
                    break
                echo.wrapped(line_out)
            if not tarball_location:
                echo.error("Cannot find tarball file location")
            else:
                instance.pull_file(name=tarball_location, destination=host_destination)
                echo.wrapped(
                    "The report tarball {} is stored on the current directory".format(
                        tarball_location.split("/")[-1]
                    )
                )

    except ProviderInstanceNotFoundError:
        _not_installed(echo)
        return 1


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

        command = ["microk8s.kubectl", "-n", "kube-system", "create", "token", "default"]
        token = instance.run(command, hide_output=True).decode().strip()

        if not token:
            echo.error("Could not generate secret token to access dashboard.")
            exit(1)

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
    except ProviderInstanceNotFoundError:
        _not_installed(echo)
        return 1


def start() -> None:
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    vm_provider_class.ensure_provider()
    instance = vm_provider_class(echoer=Echo())
    instance_info = instance.get_instance_info()
    if not instance_info.is_running():
        instance.start()
        instance.run(["microk8s.start"])


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
        instance_info = instance.get_instance_info()
        if not instance_info.is_running():
            echo.warning("MicroK8s is not running. Please run `microk8s start`.")
            return 1
        command = cmd[0]
        cmd[0] = "microk8s.{}".format(command)
        instance.run(cmd)
    except ProviderInstanceNotFoundError:
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
            if "dashboard-proxy" not in mk8s:
                complete += ["dashboard-proxy"]
            complete.sort()
            return complete
        else:
            return ["start", "stop"]
    except ProviderNotFound:
        return ["start", "stop"]


if __name__ == "__main__":
    cli()
