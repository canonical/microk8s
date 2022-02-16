#!/usr/bin/python3
import json
import os
import shutil
import subprocess
import sys

import click
import yaml

from common.utils import get_current_arch, snap_common

addons = click.Group()

repository = click.Group("repo")
addons.add_command(repository)


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
            click.echo("Use the --force flag to overwrite it".format(name), err=True)
            sys.exit(1)

        click.echo("Removing {}".format(repo_dir))
        shutil.rmtree(repo_dir)

    cmd = ["git", "clone", repository, repo_dir]
    if reference is not None:
        cmd += ["-b", reference]

    subprocess.check_call(cmd)
    subprocess.check_call(["chgrp", "microk8s", "-R", repo_dir])

    if not (repo_dir / "addons.yaml").exists():
        click.echo(
            "Error: repository '{}' does not contain an addons.yaml file".format(name), err=True
        )
        click.echo("Remove it with:", err=True)
        click.echo("    microk8s addons repo remove {}".format(name), err=True)
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
def remove(name: str):
    repo_dir = snap_common() / "addons" / name
    if not repo_dir.exists():
        click.echo("Error: repository '{}' does not exist".format(name), err=True)
        sys.exit(1)

    if not (repo_dir / ".git").exists():
        click.echo("Error: built-in repository '{}' cannot be updated".format(name), err=True)
        sys.exit(1)

    click.echo("Updating repository {}".format(name))
    subprocess.check_call(["git", "pull", "-v"], cwd=repo_dir)

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
                    ["git", "remote", "get-url", "origin"], cwd=repo_dir, stderr=subprocess.DEVNULL
                ).decode()
                revision = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=repo_dir, stderr=subprocess.DEVNULL
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
