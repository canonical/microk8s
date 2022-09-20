#!/usr/bin/env python

import click
import yaml
import os
import sys

from subprocess import check_output
from jsonschema import validate
from abc import ABC, abstractmethod


# The schema of the configuration files we can handle
schema = """
type: object
properties:
    addons:
        description: "List of addons"
        type: array
        items:
            type: object
            properties:
                name:
                    description: "Name of the addon"
                    type: string
                status:
                    description: "Should the addon be enabled or disabled"
                    enum:
                    - enable
                    - disable
                args:
                    description: "Arguments for the addon"
                    type: array
                    items:
                        type: string
            required: ["name"]
"""


class Executor(ABC):
    @abstractmethod
    def Enable(self, addon: str, args: list):
        """
        Enable an addon
        """
        pass

    @abstractmethod
    def Disable(self, addon: str, args: list):
        """
        Disable an addon
        """
        pass


class EchoCommander(Executor):
    """
    The class just prints out the commands to be executed. It is used for dry runs and debugging.
    """

    def Enable(self, addon: str, args: list):
        args_str = " ".join(args)
        click.echo(f"microk8s enable {addon} {args_str}")

    def Disable(self, addon: str, args: list):
        args_str = " ".join(args)
        click.echo(f"microk8s disable {addon} {args_str}")


class CliCommander(Executor):
    """
    This Executor calls the microk8s wrappers to apply the configuration.
    """

    def __init__(self) -> None:
        super().__init__()
        self.enable_cmd = os.path.expandvars("$SNAP/microk8s-enable.wrapper")
        self.disable_cmd = os.path.expandvars("$SNAP/microk8s-disable.wrapper")

    def Enable(self, addon: str, args: list):
        args_str = " ".join(args)
        click.echo(f"microk8s enable {addon} {args_str}")
        command = [self.enable_cmd, addon]
        if len(args) > 0:
            command = command + args
        output = check_output(command)
        click.echo(output)

    def Disable(self, addon: str, args: list):
        args_str = " ".join(args)
        click.echo(f"microk8s enable {addon} {args_str}")
        command = [self.disable_cmd, addon]
        if len(args) > 0:
            command = command + args
        output = check_output(command)
        click.echo(output)


@click.command("launcher")
@click.argument("configuration")
@click.option(
    "--dry",
    is_flag=True,
    required=False,
    default=False,
    help="Do nothing, just print the commands to be executed. (default: false)",
)
def launcher(configuration: str, dry):
    """
    Setup MicroK8s based on the provided CONFIGURATION

    CONFIGURATION is a yaml file
    """

    if not os.path.exists(configuration):
        sys.stderr.write("Please provide a yaml configuration file.\n")
        sys.exit(1)

    with open(configuration, "r") as stream:
        try:
            cfg = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            sys.stderr.write(exc)
            sys.stderr.write("Please provide a valid yaml configuration file.\n")
            sys.exit(2)

    validate(cfg, yaml.safe_load(schema))
    if dry:
        executor = EchoCommander()
    else:
        executor = CliCommander()

    for addon in cfg["addons"]:
        args = []
        if "args" in addon.keys():
            args = addon["args"]
        if "status" in addon.keys() and addon["status"] == "disable":
            executor.Disable(addon["name"], args)
        else:
            executor.Enable(addon["name"], args)


if __name__ == "__main__":
    launcher()
