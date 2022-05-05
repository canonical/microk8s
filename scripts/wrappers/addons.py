#!/usr/bin/python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

import click
import jsonschema
import yaml

from common.utils import get_current_arch, snap_common

GIT = os.path.expandvars("$SNAP/git.wrapper")

addons = click.Group()

repository = click.Group("repo")
addons.add_command(repository)


class RepoValidationError(Exception):
    @property
    def message(self) -> str:
        raise NotImplementedError()


class AddonsYamlNotFoundError(RepoValidationError):
    def __init__(self, repo_name: str):
        self.repo_name = repo_name

    @property
    def message(self) -> str:
        return f"Error: repository {self.repo_name} does not contain an addons.yaml file"


class AddonsYamlFormatError(RepoValidationError):
    def __init__(self, message):
        self._message = message

    @property
    def message(self) -> str:
        return self._message


class MissingHookError(RepoValidationError):
    def __init__(self, hook_name: str, addon: str):
        self.hook_name = hook_name
        self.addon = addon

    @property
    def message(self) -> str:
        return f"Missing {self.hook_name} hook for {self.addon} addon"


class WrongHookPermissionsError(RepoValidationError):
    def __init__(self, hook_name: str, addon: str):
        self.hook_name = hook_name
        self.addon = addon

    @property
    def message(self) -> str:
        return f"{self.hook_name} hook for {self.addon} addon needs execute permissions"


def validate_addons_repo(repo_dir: Path) -> None:
    """
    Runs some checks on an addons repository.
    Inner validations raise SystemExit if any of the validations fail.
    """
    validate_addons_file(repo_dir)
    validate_hooks(repo_dir)


def validate_addons_file(repo_dir: Path) -> None:
    """
    Checks that the addons.yaml file exists and that it has the appropriate format.
    """
    contents = load_addons_yaml(repo_dir)
    validate_yaml_schema(contents)


def load_addons_yaml(repo_dir: Path):
    addons_yaml = repo_dir / "addons.yaml"
    try:
        with open(addons_yaml, mode="r") as f:
            return yaml.safe_load(f.read())
    except FileNotFoundError:
        raise AddonsYamlNotFoundError(repo_dir.name)
    except yaml.YAMLError as err:
        message = f"Yaml format error in addons.yaml file: {err.context} {err.problem}"
        raise AddonsYamlFormatError(message)


def validate_yaml_schema(contents):
    """
    Validates that the addons.yaml file has the expected format.
    """
    schema = {
        "type": "object",
        "properties": {
            "microk8s-addons": {
                "type": "object",
                "properties": {
                    "addons": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "version": {"type": "string"},
                                "check_status": {"type": "string"},
                                "supported_architectures": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["amd64", "arm64", "s390x"],
                                    },
                                },
                            },
                            "required": [
                                "name",
                                "description",
                                "version",
                                "check_status",
                                "supported_architectures",
                            ],
                        },
                    }
                },
                "required": ["addons"],
            }
        },
        "required": ["microk8s-addons"],
    }
    try:
        jsonschema.validate(contents, schema=schema)
    except jsonschema.ValidationError as err:
        message = f"Invalid addons.yaml file: {err.message}"
        raise AddonsYamlFormatError(message)


def validate_hooks(repo_dir: Path) -> None:
    """
    Check that, for each registered addon, the enable and disable hooks
    are present in the repository, and that they have execute permissions.
    """
    for addon in get_addons_list(repo_dir):
        addon_folder = repo_dir / "addons" / addon
        for hook_name in ("enable", "disable"):
            hook = addon_folder / hook_name
            if not hook.exists():
                raise MissingHookError(hook_name, addon)
            if not os.access(hook, os.X_OK):
                raise WrongHookPermissionsError(hook_name, addon)


def get_addons_list(repo_dir: Path) -> List[str]:
    contents = load_addons_yaml(repo_dir)
    return [addon["name"] for addon in contents["microk8s-addons"]["addons"]]


@repository.command("add", help="Add a MicroK8s addons repository")
@click.argument("name")
@click.argument("repository")
@click.option("--reference")
@click.option("--force", is_flag=True, default=False)
def add(name: str, repository: str, reference: str, force: bool):
    repo_dir = snap_common() / "addons" / name
    if repo_dir.exists():
        if not force:
            click.echo("Error: repository '{}' already exists!".format(name), err=True)
            click.echo("Use the --force flag to overwrite it", err=True)
            sys.exit(1)

        click.echo("Removing {}".format(repo_dir))
        shutil.rmtree(repo_dir)

    cmd = [GIT, "clone", repository, repo_dir]
    if reference is not None:
        cmd += ["-b", reference]
    subprocess.check_call(cmd)
    subprocess.check_call(["chgrp", "microk8s", "-R", repo_dir])

    try:
        validate_addons_repo(repo_dir)
    except RepoValidationError as err:
        click.echo(err.message, err=True)
        click.echo(f"Removing {repo_dir}")
        shutil.rmtree(repo_dir)
        sys.exit(1)


@repository.command("remove", help="Remove a MicroK8s addons repository")
@click.argument("name")
def remove(name: str):
    repo_dir = snap_common() / "addons" / name
    if not repo_dir.exists():
        click.echo("Error: repository '{}' does not exist".format(name), err=True)
        sys.exit(1)

    click.echo("Removing {}".format(repo_dir))
    shutil.rmtree(repo_dir)


@repository.command("update", help="Update a MicroK8s addons repository")
@click.argument("name")
def update(name: str):
    repo_dir = snap_common() / "addons" / name
    if not repo_dir.exists():
        click.echo("Error: repository '{}' does not exist".format(name), err=True)
        sys.exit(1)

    if not (repo_dir / ".git").exists():
        click.echo("Error: built-in repository '{}' cannot be updated".format(name), err=True)
        sys.exit(1)

    click.echo("Updating repository {}".format(name))
    subprocess.check_call([GIT, "pull"], cwd=repo_dir)

    if not (repo_dir / "addons.yaml").exists():
        click.echo(
            "Error: repository '{}' does not contain an addons.yaml file".format(name), err=True
        )
        click.echo("Remove it with:", err=True)
        click.echo("    microk8s addons repo remove {}".format(name), err=True)
        sys.exit(1)


@repository.command("list", help="List configured MicroK8s addons repositories")
@click.option("--format", default="table", type=click.Choice(["json", "yaml", "table"]))
def list(format: str):
    arch = get_current_arch()
    repositories = []
    for dir in os.listdir(snap_common() / "addons"):
        try:
            repo_dir = snap_common() / "addons" / dir
            addons_yaml = repo_dir / "addons.yaml"
            with open(addons_yaml, "r") as fin:
                addons = yaml.safe_load(fin)

            count = 0
            for addon in addons["microk8s-addons"]["addons"]:
                if arch in addon["supported_architectures"]:
                    count += 1

            source = "(built-in)"
            try:
                remote_url = subprocess.check_output(
                    [GIT, "remote", "get-url", "origin"], cwd=repo_dir, stderr=subprocess.DEVNULL
                ).decode()
                revision = subprocess.check_output(
                    [GIT, "rev-parse", "HEAD"], cwd=repo_dir, stderr=subprocess.DEVNULL
                ).decode()[:6]
                source = "{}@{}".format(remote_url.strip(), revision.strip())
            except (subprocess.CalledProcessError, TypeError, ValueError):
                pass

            repositories.append(
                {
                    "name": dir,
                    "addons": count,
                    "source": source,
                    "description": addons["microk8s-addons"]["description"],
                }
            )

        except Exception as e:
            click.echo("could not load addons from {}: {}".format(addons_yaml, e), err=True)

    if format == "json":
        click.echo(json.dumps(repositories))
    elif format == "yaml":
        click.echo(yaml.safe_dump(repositories))
    elif format == "table":
        click.echo(("{:10} {:>6} {}").format("REPO", "ADDONS", "SOURCE"))
        for repo in repositories:
            click.echo("{:10} {:>6} {}".format(repo["name"], repo["addons"], repo["source"]))


if __name__ == "__main__":
    addons(prog_name="microk8s addons")
