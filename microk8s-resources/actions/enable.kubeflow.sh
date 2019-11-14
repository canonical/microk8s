#!/usr/bin/env python3

import argparse
import json
import os
import random
import string
import subprocess
import sys
import tempfile
import textwrap
import time


def run(*args, die=True):
    # Add wrappers to $PATH
    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

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
            if result.stderr:
                print(result.stderr.decode("utf-8"))
            print(err)
            sys.exit(1)
        else:
            raise

    return result.stdout.decode("utf-8")


def get_random_pass():
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(30)
    )


def juju(*args, **kwargs):
    if "KUBEFLOW_DEBUG" in os.environ:
        return run("microk8s-juju.wrapper", "--debug", *args, **kwargs)
    else:
        return run("microk8s-juju.wrapper", *args, **kwargs)


def main():
    password = os.environ.get("KUBEFLOW_AUTH_PASSWORD") or get_random_pass()
    channel = os.environ.get("KUBEFLOW_CHANNEL") or "stable"

    password_overlay = {
        "applications": {
            "katib-db": {"options": {"root_password": get_random_pass()}},
            "kubeflow-gatekeeper": {"options": {"password": password}},
            "modeldb-db": {"options": {"root_password": get_random_pass()}},
            "pipelines-api": {"options": {"minio-secret-key": "minio123"}},
            "pipelines-db": {"options": {"root_password": get_random_pass()}},
        }
    }

    for service in ["dns", "storage", "dashboard", "ingress", "rbac", "juju"]:
        print("Enabling %s..." % service)
        run("microk8s-enable.wrapper", service)

    try:
        juju("show-controller", "uk8s", die=False)
    except subprocess.CalledProcessError:
        pass
    else:
        print("Kubeflow has already been enabled.")
        sys.exit(1)

    print("Deploying Kubeflow...")
    juju("bootstrap", "microk8s", "uk8s")
    juju("add-model", "kubeflow", "microk8s")

    with tempfile.NamedTemporaryFile("w+") as f:
        json.dump(password_overlay, f)
        f.flush()

        juju("deploy", "kubeflow", "--channel", channel, "--overlay", f.name)

    print("Kubeflow deployed.")
    print("Waiting for operator pods to become ready.")
    for _ in range(80):
        status = json.loads(juju("status", "-m", "uk8s:kubeflow", "--format=json"))
        unready_apps = [
            name
            for name, app in status["applications"].items()
            if "message" in app["application-status"]
        ]
        if unready_apps:
            print("Still waiting for %s operator pods..." % len(unready_apps))
            time.sleep(15)
        else:
            break
    else:
        print("Waited too long for Kubeflow to become ready!")
        sys.exit(1)

    print("Operator pods ready.")
    print("Waiting for service pods to become ready.")
    run(
        "microk8s-kubectl.wrapper",
        "wait",
        "--namespace=kubeflow",
        "--for=condition=Ready",
        "pod",
        "--timeout=600s",
        "--all",
    )

    juju("config", "ambassador", "juju-external-hostname=localhost")
    juju("expose", "ambassador")

    # Workaround for https://bugs.launchpad.net/juju/+bug/1849725.
    # Wait for up to a minute for Juju to finish setting up the Ingress
    # so that we can patch it, and fail if it takes too long.
    patch = json.dumps({
        'kind': 'Ingress',
        'apiVersion': 'extensions/v1beta1',
        'metadata': {'name': 'ambassador', 'namespace': 'kubeflow'},
        'spec': {'tls': [{'hosts': ['localhost'], 'secretName': 'ambassador-tls'}]},
    }).encode('utf-8')

    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

    for _ in range(12):
        try:
            subprocess.run(
                ['microk8s-kubectl.wrapper', 'apply', '-f', '-'],
                input=patch,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                env=env,
            ).check_returncode()
            break
        except subprocess.CalledProcessError:
            time.sleep(5)
    else:
        print("Couldn't set Ambassador up properly")
        sys.exit(1)

    print(
        textwrap.dedent(
            """
    Congratulations, Kubeflow is now available.
    The dashboard is available at https://localhost/
    To tear down Kubeflow and associated infrastructure, run:

       microk8s.disable kubeflow
    """
        )
    )


if __name__ == "__main__":
    main()
