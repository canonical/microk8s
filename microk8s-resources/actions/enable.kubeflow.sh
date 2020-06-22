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
from distutils.util import strtobool
from itertools import count
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urlparse

MIN_MEM_GB = 14
CONNECTIVITY_CHECKS = [
    'https://api.jujucharms.com/charmstore/v5/~kubeflow-charmers/ambassador-88/icon.svg',
]


def run(*args, die=True, debug=False, stdout=True):
    # Add wrappers to $PATH
    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

    if debug and stdout:
        print("\033[;1;32m+ %s\033[;0;0m" % " ".join(args))

    result = subprocess.run(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
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

    result_stdout = result.stdout.decode("utf-8")

    if debug and stdout:
        print(result_stdout)
        if result.stderr:
            print(result.stderr.decode("utf-8"))

    return result_stdout


def get_random_pass():
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(30))


def juju(*args, **kwargs):
    if strtobool(os.environ.get("KUBEFLOW_DEBUG") or "false"):
        return run("microk8s-juju.wrapper", "--debug", *args, debug=True, **kwargs)
    else:
        return run("microk8s-juju.wrapper", *args, **kwargs)


def get_hostname():
    """Gets the hostname that Ambassador will respond to."""

    # Check if we've manually set a hostname on the ingress
    try:
        output = run(
            "microk8s-kubectl.wrapper",
            "get",
            "--namespace=kubeflow",
            "ingress/ambassador",
            "-ojson",
            stdout=False,
            die=False,
        )
        return json.loads(output)["spec"]["rules"][0]["host"]
    except (KeyError, subprocess.CalledProcessError):
        pass

    # Otherwise, see if we've set up metallb with a custom service
    try:
        output = run(
            "microk8s-kubectl.wrapper",
            "get",
            "--namespace=kubeflow",
            "svc/ambassador",
            "-ojson",
            stdout=False,
            die=False,
        )
        pub_ip = json.loads(output)["status"]["loadBalancer"]["ingress"][0]["ip"]
        return "%s.xip.io" % pub_ip
    except (KeyError, subprocess.CalledProcessError):
        pass

    # If all else fails, just use localhost
    return "localhost"


def main():
    password = os.environ.get("KUBEFLOW_AUTH_PASSWORD") or get_random_pass()
    bundle = os.environ.get("KUBEFLOW_BUNDLE") or "cs:kubeflow-195"
    channel = os.environ.get("KUBEFLOW_CHANNEL") or "stable"
    no_proxy = os.environ.get("KUBEFLOW_NO_PROXY") or None
    hostname = os.environ.get("KUBEFLOW_HOSTNAME") or None
    debug = strtobool(os.environ.get("KUBEFLOW_DEBUG") or "false")
    ignore_min_mem = strtobool(os.environ.get("KUBEFLOW_IGNORE_MIN_MEM") or "false")

    with open("/proc/meminfo") as f:
        memtotal_lines = [l for l in f.readlines() if "MemTotal" in l]

    try:
        total_mem = int(memtotal_lines[0].split(" ")[-2])
    except IndexError:
        print("Couldn't determine total memory.")
        print("Kubeflow recommends at least %s GB of memory." % MIN_MEM_GB)

    if total_mem < MIN_MEM_GB * 1024 * 1024 and not ignore_min_mem:
        print("Kubeflow recommends at least %s GB of memory." % MIN_MEM_GB)
        print(
            "Run `KUBEFLOW_IGNORE_MIN_MEM=true microk8s.enable kubeflow`"
            " if you'd like to proceed anyways."
        )
        sys.exit(1)

    for url in CONNECTIVITY_CHECKS:
        try:
            response = urlopen(url)
        except URLError:
            host = urlparse(url).netloc
            print("Couldn't contact %s" % host)
            print("Please check your network connectivity before enabling Kubeflow.")
            sys.exit(1)

        if response.status != 200:
            print("URL connectivity check failed with response %s" % response.status)
            print("Please check your network connectivity before enabling Kubeflow.")
            sys.exit(1)

    password_overlay = {
        "applications": {
            "dex-auth": {"options": {"static-username": "admin", "static-password": password}},
            "katib-db": {"options": {"root_password": get_random_pass()}},
            "modeldb-db": {"options": {"root_password": get_random_pass()}},
            "oidc-gatekeeper": {"options": {"client-secret": get_random_pass()}},
            "pipelines-api": {"options": {"minio-secret-key": "minio123"}},
            "pipelines-db": {"options": {"root_password": get_random_pass()}},
        }
    }

    for service in [
        "dns",
        "storage",
        "dashboard",
        "ingress",
        "metallb:10.64.140.43-10.64.140.49",
    ]:
        print("Enabling %s..." % service)
        run("microk8s-enable.wrapper", service, debug=debug)

    run("microk8s-status.wrapper", "--wait-ready", debug=debug)

    print("Waiting for DNS and storage plugins to finish setting up")
    run(
        "microk8s-kubectl.wrapper",
        "wait",
        "--for=condition=available",
        "-nkube-system",
        "deployment/coredns",
        "deployment/hostpath-provisioner",
        "--timeout=10m",
        debug=debug,
    )

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

        juju("deploy", bundle, "--channel", channel, "--overlay", f.name)

    print("Kubeflow deployed.")
    print("Waiting for operator pods to become ready.")
    wait_seconds = 15
    for i in count():
        status = json.loads(juju("status", "-m", "uk8s:kubeflow", "--format=json", stdout=False))
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
        debug=debug,
    )

    with tempfile.NamedTemporaryFile(mode='w+') as f:
        json.dump(
            {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {'labels': {'juju-app': 'pipelines-api'}, 'name': 'ml-pipeline',},
                'spec': {
                    'ports': [
                        {'name': 'grpc', 'port': 8887, 'protocol': 'TCP', 'targetPort': 8887},
                        {'name': 'http', 'port': 8888, 'protocol': 'TCP', 'targetPort': 8888},
                    ],
                    'selector': {'juju-app': 'pipelines-api'},
                    'type': 'ClusterIP',
                },
            },
            f,
        )
        f.flush()
        run('microk8s-kubectl.wrapper', 'apply', '-f', f.name)

    run(
        'microk8s-kubectl.wrapper',
        'delete',
        'mutatingwebhookconfigurations/katib-mutating-webhook-config',
        'validatingwebhookconfigurations/katib-validating-webhook-config',
    )

    hostname = hostname or get_hostname()
    juju("config", "dex-auth", "public-url=http://%s:80" % hostname)
    juju("config", "oidc-gatekeeper", "public-url=http://%s:80" % hostname)
    juju("config", "ambassador", "juju-external-hostname=%s" % hostname)
    juju("expose", "ambassador")

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
