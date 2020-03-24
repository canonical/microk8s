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
            print("Kubeflow could not be enabled:")
            if result.stderr:
                print(result.stderr.decode("utf-8"))
            print(err)
            sys.exit(1)
        else:
            raise

    result_stdout = result.stdout.decode('utf-8')

    if debug and stdout:
        print(result_stdout)
        if result.stderr:
            print(result.stderr.decode('utf-8'))

    return result_stdout


def get_random_pass():
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(30)
    )


def juju(*args, **kwargs):
    if strtobool(os.environ.get("KUBEFLOW_DEBUG") or "false"):
        return run('microk8s-juju.wrapper', "--debug", *args, debug=True, **kwargs)
    else:
        return run('microk8s-juju.wrapper', *args, **kwargs)


def main():
    password = os.environ.get("KUBEFLOW_AUTH_PASSWORD") or get_random_pass()
    channel = os.environ.get("KUBEFLOW_CHANNEL") or "stable"
    no_proxy = os.environ.get("KUBEFLOW_NO_PROXY") or None
    hostname = os.environ.get("KUBEFLOW_HOSTNAME") or "localhost"

    password_overlay = {
        "applications": {
            "dex-auth": {
                "options": {
                    "public-url": hostname,
                    "static-username": "admin",
                    "static-password": password,
                }
            },
            "katib-db": {"options": {"root_password": get_random_pass()}},
            "modeldb-db": {"options": {"root_password": get_random_pass()}},
            "oidc-gatekeeper": {
                "options": {"public-url": hostname, "client-secret": get_random_pass()}
            },
            "pipelines-api": {"options": {"minio-secret-key": "minio123"}},
            "pipelines-db": {"options": {"root_password": get_random_pass()}},
        }
    }

    for service in ["dns", "storage", "rbac", "dashboard", "ingress", "metallb:10.64.140.43-10.64.140.49"]:
        print("Enabling %s..." % service)
        run("microk8s-enable.wrapper", service)

    run("microk8s-status.wrapper", '--wait-ready')

    try:
        juju("show-controller", "uk8s", die=False, stdout=False)
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

    for _ in range(240):
        try:
            juju(
                'kubectl',
                'wait',
                '--for=condition=ready',
                'pod/cert-manager-webhook-operator-0',
                die=False,
            )
            break
        except subprocess.CalledProcessError:
            time.sleep(5)
    else:
        print("Waited too long for cert manager webhook operator pod to appear.")
        sys.exit(1)

    run(
        "microk8s-kubectl.wrapper",
        'patch',
        'role',
        '-n',
        'kubeflow',
        'cert-manager-webhook-operator',
        '-p',
        json.dumps(
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'Role',
                'metadata': {'name': 'cert-manager-webhook-operator'},
                'rules': [
                    {'apiGroups': [''], 'resources': ['pods'], 'verbs': ['get', 'list']},
                    {'apiGroups': [''], 'resources': ['pods/exec'], 'verbs': ['create']},
                    {'apiGroups': [''], 'resources': ['secrets'], 'verbs': ['get', 'list']},
                ],
            }
        ),
    )

    print("Kubeflow deployed.")
    print("Waiting for operator pods to become ready.")
    wait_seconds = 15
    for i in count():
        status = json.loads(
            juju("status", "-m", "uk8s:kubeflow", "--format=json", stdout=False)
        )
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

    # Workaround for https://bugs.launchpad.net/juju/+bug/1849725.
    ingress = json.dumps(
        {
            "apiVersion": "extensions/v1beta1",
            "kind": "Ingress",
            "metadata": {"name": "ambassador-ingress", "namespace": "kubeflow"},
            "spec": {
                "rules": [
                    {
                        "host": hostname,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "serviceName": "ambassador",
                                        "servicePort": 80,
                                    },
                                    "path": "/",
                                }
                            ]
                        },
                    }
                ],
                "tls": [{"hosts": [hostname], "secretName": "dummy-tls"}],
            },
        }
    ).encode("utf-8")

    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

    subprocess.run(
        ["microk8s-kubectl.wrapper", "apply", "-f", "-"],
        input=ingress,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=env,
    ).check_returncode()

    print(
        textwrap.dedent(
            """
    Congratulations, Kubeflow is now available.
    The dashboard is available at http://%s/

        Username: admin
        Password: %s

    To see these values again, run:

        microk8s juju config dex-auth static-username
        microk8s juju config dex-auth static-password

    To tear down Kubeflow and associated infrastructure, run:

       microk8s disable kubeflow
    """
            % (hostname, password)
        )
    )


if __name__ == "__main__":
    main()
