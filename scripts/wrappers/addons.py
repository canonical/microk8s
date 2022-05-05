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
    try:
        contents = load_addons_yaml(repo_dir)
    except FileNotFoundError:
        repo_name = repo_dir.name
        click.echo(
            f"Error: repository '{repo_name}' does not contain an addons.yaml file", err=True
        )
        click.echo("Remove it with:", err=True)
        click.echo(f"    microk8s addons repo remove {repo_name}", err=True)
        sys.exit(1)
    except yaml.YAMLError as err:
        click.echo(f"Yaml format error in addons.yaml file: {err}", err=True)
        sys.exit(1)

    try:
        validate_yaml_schema(contents)
    except jsonschema.ValidationError as err:
        click.echo(f"Invalid addons.yaml file: {err.message}", err=True)
        sys.exit(1)


def load_addons_yaml(repo_dir: Path):
    addons_yaml = repo_dir / "addons.yaml"
    with open(addons_yaml, mode="r") as f:
        return yaml.safe_load(f.read())


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
    jsonschema.validate(contents, schema=schema)


def validate_hooks(repo_dir: Path) -> None:
    """
    Check that enable and disable hooks are present in the
    repository, and that they have execute permissions.
    """
    for addon in get_addons_list(repo_dir):
        addon_folder = repo_dir / "addons" / addon
        for hook_name in ("enable", "disable"):
            hook = addon_folder / hook_name
            check_exists(hook)
            check_is_executable(addon_folder)


def get_addons_list(repo_dir: Path) -> List[str]:
    contents = load_addons_yaml(repo_dir)
    return [addon["name"] for addon in contents["microk8s-addons"]["addons"]]


def check_exists(hook: Path):
    if not hook.exists():
        click.echo(f"Missing {hook.name} hook", err=True)
        sys.exit(1)


def check_is_executable(hook: Path):
    if not os.access(hook, os.X_OK):
        click.echo(
            f"{hook.name} hook needs execute permissions. Try with: chmod a+x {hook}", err=True
        )
        sys.exit(1)


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

    validate_addons_repo(repo_dir)


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
