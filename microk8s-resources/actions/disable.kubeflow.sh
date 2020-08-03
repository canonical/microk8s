#!/usr/bin/env python3

import os
import subprocess

import click


@click.command()
def kubeflow():
    click.echo("Disabling Kubeflow...")

    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

    click.echo("Unregistering model...")
    try:
        subprocess.run(
            ['microk8s-juju.wrapper', 'unregister', '-y', 'uk8s'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
    except subprocess.CalledProcessError:
        pass
    click.echo("Unregistering complete.")

    click.echo("Destroying namespace...")
    try:
        subprocess.check_call(
            ['microk8s-kubectl.wrapper', 'delete', 'ns', 'controller-uk8s', 'kubeflow'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
    except subprocess.CalledProcessError:
        pass
    click.echo("Destruction complete.")

    click.echo("Kubeflow is now disabled.")


if __name__ == "__main__":
    kubeflow(prog_name='microk8s disable kubeflow')
