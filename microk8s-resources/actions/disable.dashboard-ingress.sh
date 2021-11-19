#!/usr/bin/env python3

import os
import subprocess

import click

@click.command()
def dashboard_ingress():
    click.echo("Disabling Ingress for Kubernetes Dashboard")

    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]  

    resources = [
        "secret/kubernetes-dashboard-basic-auth",
        "ingress.networking.k8s.io/kubernetes-dashboard-ingress"
    ] 

    for resource in resources:
        click.echo(f"Destroying {resource}...")
        try:
            subprocess.check_call(
                ["microk8s-kubectl.wrapper", "delete", "-n", "kube-system", resource],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
        except subprocess.CalledProcessError:
            pass

    click.echo("Destruction complete.")
    click.echo("Ingress for Kubernetes Dashboard is disabled")

if __name__ == "__main__":
    dashboard_ingress(prog_name="microk8s disable dashboard-ingress")
