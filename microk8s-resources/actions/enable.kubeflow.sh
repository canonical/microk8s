#!/usr/bin/env python3

import json
import os
import random
import string
import subprocess
import sys
import tempfile
import textwrap
import time
from itertools import count
from distutils.util import strtobool


def run(*args, die=True, debug=False):
    # Add wrappers to $PATH
    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

    if debug:
        print("Running `%s`" % ' '.join(args))

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
            print("Kubeflow could not be enabled:")
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
    if strtobool(os.environ.get("KUBEFLOW_DEBUG") or 'false'):
        return run("microk8s-juju.wrapper", "--debug", *args, debug=True, **kwargs)
    else:
        return run("microk8s-juju.wrapper", *args, **kwargs)


def main():
    password = os.environ.get("KUBEFLOW_AUTH_PASSWORD") or get_random_pass()
    channel = os.environ.get("KUBEFLOW_CHANNEL") or "stable"
    no_proxy = os.environ.get("KUBEFLOW_NO_PROXY") or None

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
    if no_proxy is not None:
        juju("bootstrap", "microk8s", "uk8s", "--config=juju-no-proxy=%s" % no_proxy)
        juju("add-model", "kubeflow", "microk8s")
        juju("model-config", "-m", "kubeflow", "juju-no-proxy=%s" % no_proxy)
    else:
        juju("bootstrap", "microk8s", "uk8s")
        juju("add-model", "kubeflow", "microk8s")

    with tempfile.NamedTemporaryFile("w+") as f:
        json.dump(password_overlay, f)
        f.flush()

        juju("deploy", "cs:kubeflow", "--channel", channel, "--overlay", f.name)

    print("Kubeflow deployed.")
    print("Waiting for operator pods to become ready.")
    wait_seconds = 15
    for i in count():
        status = json.loads(juju("status", "-m", "uk8s:kubeflow", "--format=json"))
        unready_apps = [
            name
            for name, app in status["applications"].items()
            if "message" in app["application-status"]
        ]
        if unready_apps:
            print(
                "Waited %ss for operator pods to come up, %s remaining."
                % (wait_seconds * i, len(unready_apps))
            )
            time.sleep(wait_seconds)
        else:
            break

    print("Operator pods ready.")
    print("Waiting for service pods to become ready.")
    run(
        "microk8s-kubectl.wrapper",
        "wait",
        "--namespace=kubeflow",
        "--for=condition=Ready",
        "pod",
        "--timeout=-1s",
        "--all",
    )

    juju("config", "ambassador", "juju-external-hostname=microk8s.local")
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
    The dashboard is available at https://microk8s.local/

        Username: admin
        Password: %s

    To see these values again, run:

        microk8s.juju config kubeflow-gatekeeper username
        microk8s.juju config kubeflow-gatekeeper password

    To tear down Kubeflow and associated infrastructure, run:

       microk8s.disable kubeflow
    """
            % (password_overlay["applications"]["kubeflow-gatekeeper"]["options"]["password"])
        )
    )


if __name__ == "__main__":
    main()
