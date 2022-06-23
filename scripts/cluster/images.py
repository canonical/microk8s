#!/usr/bin/python3
import os
import subprocess
import sys
from typing import List

import click

from distributed_op import do_image_import

CTR = "{}/microk8s-ctr.wrapper".format(os.getenv("SNAP"))

images = click.Group()


@images.command("import", help="Import OCI images into the MicroK8s cluster")
@click.argument("image", default="-")
def import_images(image: str):

    if image == "-":
        image_data = sys.stdin.buffer.read()
    else:
        try:
            with open(image, "rb") as fin:
                image_data = fin.read()
        except OSError as e:
            click.echo("Error: failed to read {}: {}".format(image, e), err=True)
            sys.exit(1)

    do_image_import(image_data)


def get_all_ctr_images():
    """
    Return list of all OCI images from containerd.
    """
    images = subprocess.check_output([CTR, "image", "ls", "--quiet"]).decode().split("\n")

    # drop the sha256-digest aliases
    return [tag for tag in images if tag and not tag.startswith("sha256:")]


@images.command("export-local", help="Export OCI images from the current MicroK8s node")
@click.argument("output", default="-")
@click.argument("images", nargs=-1)
def export_images(output: str, images: List[str]):
    if not images:
        images = get_all_ctr_images()

    for image in images:
        click.echo("Checking {}".format(image), err=True)
        try:
            subprocess.check_call([CTR, "image", "export", "-", image], stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            subprocess.check_call(
                [CTR, "content", "fetch", "--all-platforms", image], stdout=sys.stderr
            )

    subprocess.check_call([CTR, "image", "export", output, *images])


if __name__ == "__main__":
    images(prog_name="microk8s images")
