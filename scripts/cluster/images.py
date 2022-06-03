#!/usr/bin/python3
import sys

import click

from distributed_op import do_image_import

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


if __name__ == "__main__":
    images(prog_name="microk8s images")
