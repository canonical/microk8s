#!/usr/bin/env python3

import os
import sys
import subprocess
import crypt
import random
import json
import string
import tempfile
from base64 import b64encode

from ipaddress import ip_address
import click


def run(*args, die=True, debug=False, stdout=True):
    # Add wrappers to $PATH
    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

    if debug and stdout:
        print("\033[;1;32m+ %s\033[;0;0m" % " ".join(args))

    result = subprocess.run(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        result.check_returncode()
    except subprocess.CalledProcessError as err:
        if die:
            print("Ingress for Kubernetes Dashboard could not be enabled:")
            if result.stderr:
                print(result.stderr.decode("utf-8"))
            print(err)
            sys.exit(1)
        else:
            raise

    result_stdout = result.stdout.decode("utf-8")

    if debug and stdout:
        print(result_stdout)
        if result.stderr:
            print(result.stderr.decode("utf-8"))

    return result_stdout


def htpasswd(pw, salt_length=32) -> str:
    """Generates an htpasswd hash from provided password pw."""
    return crypt.crypt(pw, get_random_pass(salt_length))


def valid_ip(ip) -> bool:
    """Validates whether the provided IP is formatted correctly."""
    try:
        _ = ip_address(ip)
        return True
    except ValueError:
        return False


def enable_addons(debug=False, addons=("ingress", "dashboard")):
    for addon in addons:
        print("Enabling %s..." % addon)
        run("microk8s-enable.wrapper", addon, debug=debug)


def get_random_pass(length=32) -> str:
    """Generates a random password."""
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


@click.command()
@click.option(
    "--hostname", "-n",
    default="kubernetes-dashboard.127.0.0.1.nip.io",
    help="Sets the virtual hostname assigned to Kubernetes Dashboard."
)
@click.option(
    "--allow", "-a",
    multiple=True,
    default=['127.0.0.1/8', '169.254.0.0/16', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'],
    help="Allow a subnet to access the Kubernetes Dashboard."
)
@click.option(
    "--auth",
    is_flag=True,
    help="If true, enables HTTP basic authentication."
)
@click.option(
    "--auth-user",
    default="admin",
    help="The username for HTTP basic authentication"
)
@click.password_option(
    envvar="DASHBOARD_INGRESS_AUTH_PASSWORD",
    default=get_random_pass,
    prompt=False,
    help="The password for HTTP basic authentication."
)
def dashboard_ingress(hostname, allow, auth, auth_user, password):
    click.echo("Enabling Ingress for Kubernetes Dashboard")
    enable_addons(addons=("ingress", "dashboard"))

    click.echo("Applying manifest")
    manifest = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "name": "kubernetes-dashboard-ingress",
            "namespace": "kube-system",
            "annotations": {
                "kubernetes.io/ingress.class": "public",

                # restrict to private network scopes
                "nginx.ingress.kubernetes.io/whitelist-source-range": ",".join(allow),

                "nginx.ingress.kubernetes.io/force-ssl-redirect": "true",
                "nginx.ingress.kubernetes.io/ssl-passthrough": "true",
                "nginx.ingress.kubernetes.io/backend-protocol": "HTTPS"
            }
        },
        "spec": {
            "rules": [{
                "host": hostname,
                "http": {
                    "paths": [{
                        "path": "/",
                        "pathType": "Prefix",
                        "backend": {
                            "service": {
                                "name": "kubernetes-dashboard",
                                "port": {"number": 443}
                            }
                        }
                    }]
                }

            }]
        }
    }

    if auth:
        click.echo("Configuring authentication")
        encoded_auth = b64encode(f"{auth_user}:{htpasswd(password)}".encode("utf-8")).decode("utf-8")

        with tempfile.NamedTemporaryFile(mode="w+") as f:
            json.dump({
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": "kubernetes-dashboard-basic-auth",
                    "namespace": "kube-system"
                },
                "data": {"auth": encoded_auth},
                "type": "Opaque"
            }, f)
            f.flush()

            run(
                "microk8s-kubectl.wrapper",
                "apply",
                "-f",
                f.name,
                die=False,
                stdout=False
            )

        manifest["metadata"]["annotations"].update({
            "nginx.ingress.kubernetes.io/auth-type": "basic",
            "nginx.ingress.kubernetes.io/auth-secret": "kubernetes-dashboard-basic-auth",
            "nginx.ingress.kubernetes.io/auth-realm": "Authentication Required - Kubernetes Dashboard"
        })

    with tempfile.NamedTemporaryFile(mode="w+") as f:
        json.dump(manifest, f)
        f.flush()

        run("microk8s-kubectl.wrapper", "apply", "-f", f.name)

    click.echo("Ingress for Kubernetes Dashboard is enabled.")
    click.echo(f"\nDashboard will be available at https://{hostname}")

    if auth:
        click.echo("HTTP basic authentication login:")
        click.echo(f"Username: {auth_user}")
        click.echo(f"Password: {password}")

if __name__ == "__main__":
    dashboard_ingress(prog_name="microk8s enable dashboard-ingress")
