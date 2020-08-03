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
from pathlib import Path
from urllib.error import URLError
from urllib.parse import ParseResult, urlparse
from urllib.request import urlopen
import click


MIN_MEM_GB = 14
CONNECTIVITY_CHECKS = [
    'https://api.jujucharms.com/charmstore/v5/~kubeflow-charmers/ambassador-88/icon.svg',
]


def kubectl_exists(resource):
    try:
        run('microk8s-kubectl.wrapper', 'get', '-nkubeflow', resource, die=False)
        return True
    except subprocess.CalledProcessError:
        return False


def retry_run(*args, die=True, debug=False, stdout=True, times=3):
    for attempt in range(1, times + 1):
        try:
            return run(*args, die=(times == attempt and die), debug=debug, stdout=stdout)
        except subprocess.CalledProcessError as err:
            if times == attempt:
                raise
            else:
                if debug and stdout:
                    print(err)
                    print("Retrying.")


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


def check_connectivity():
    """Checks connectivity to URLs from within and without the cluster.

    For each URL in `CONNECTIVITY_CHECKS`, checks that the URL is reachable from
    the host, then spins up a pod and checks from within MicroK8s.
    """

    for url in CONNECTIVITY_CHECKS:
        host = urlparse(url).netloc
        try:
            response = urlopen(url)
        except URLError:
            print("Couldn't contact %s" % host)
            print("Please check your network connectivity before enabling Kubeflow.")
            sys.exit(1)

        if response.status != 200:
            print("URL connectivity check failed with response %s" % response.status)
            print("Please check your network connectivity before enabling Kubeflow.")
            sys.exit(1)

        try:
            run(
                'microk8s-kubectl.wrapper',
                'run',
                '--rm',
                '-i',
                '--restart=Never',
                '--image=ubuntu',
                'connectivity-check',
                '--',
                'bash',
                '-c',
                'apt update && apt install -y curl && curl %s' % url,
                die=False,
                stdout=False,
            )
        except subprocess.CalledProcessError:
            print("Couldn't contact %s from within the Kubernetes cluster" % host)
            print("Please check your network connectivity before enabling Kubeflow.")
            sys.exit(1)


def parse_hostname(hostname: str) -> ParseResult:
    if '//' in hostname:
        parsed = urlparse(hostname)
    else:
        parsed = urlparse('//' + hostname)

    if not parsed.scheme:
        parsed = parsed._replace(scheme='http')

    if not parsed.hostname:
        print("Manual hostname `%s` leaves hostname unspecified" % hostname)
        sys.exit(1)

    if not parsed.port:
        parsed = parsed._replace(netloc=parsed.hostname or '' + (parsed.port or ''))

    if parsed.path not in ('', '/'):
        print("WARNING: The path `%s` was set on the hostname, but was ignored." % parsed.path)

    if parsed.params:
        print(
            "WARNING: The params `%s` were set on the hostname, but were ignored." % parsed.params
        )

    if parsed.query:
        print("WARNING: The query `%s` was set on the hostname, but was ignored." % parsed.query)

    if parsed.params:
        print(
            "WARNING: The fragment `%s` was set on the hostname, but was ignored." % parsed.fragment
        )

    return parsed._replace(path='', params='', query='', fragment='')


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


@click.command()
@click.option(
    '--bundle',
    default='cs:kubeflow-230',
    help='The Kubeflow bundle to deploy. Can be one of full, lite, edge, or a charm store URL.',
)
@click.option(
    '--channel',
    default='stable',
    type=click.Choice(['stable', 'candidate', 'beta', 'edge']),
    help='Which channel to deploy the bundle from. In most cases, this should be `stable`.',
)
@click.option(
    '--debug/--no-debug',
    default=False,
    help='If true, shows more verbose output when enabling Kubeflow.',
)
@click.option(
    '--hostname',
    help='If set, this hostname is used instead of a hostname generated by MetalLB.',
)
@click.option(
    '--ignore-min-mem/--no-ignore-min-mem',
    default=False,
    help='If set, overrides the minimum memory check.',
)
@click.option(
    '--no-proxy',
    help='Allows setting the juju-no-proxy configuration option.',
)
@click.password_option(
    envvar='KUBEFLOW_AUTH_PASSWORD',
    default=get_random_pass,
    help='The Kubeflow dashboard password.',
)
def kubeflow(bundle, channel, debug, hostname, ignore_min_mem, no_proxy, password):
    if os.geteuid() == 0:
        print("This command can't be run as root.")
        print("Try `microk8s enable kubeflow` instead.")
        sys.exit(1)

    juju_path = Path(os.environ['SNAP_DATA']) / 'juju'
    if juju_path.stat().st_gid == 0:
        print("Found bad permissions on %s, fixing..." % juju_path)
        try:
            run('sudo', 'chgrp', '-R', 'microk8s', str(juju_path), die=False)
            run('sudo', 'chmod', '-R', '775', str(juju_path), die=False)
        except subprocess.CalledProcessError as err:
            print("Encountered error while attempting to fix permissions:")
            print(err)
            print("You can attempt to fix this yourself with:\n")
            print("sudo chgrp -R microk8s %s" % juju_path)
            print("sudo chmod -R 775 %s\n" % juju_path)
            sys.exit(1)

    with open("/proc/meminfo") as f:
        memtotal_lines = [line for line in f.readlines() if "MemTotal" in line]

    try:
        total_mem = int(memtotal_lines[0].split(" ")[-2])
    except IndexError:
        print("Couldn't determine total memory.")
        print("Kubeflow recommends at least %s GB of memory." % MIN_MEM_GB)

    if total_mem < MIN_MEM_GB * 1024 * 1024 and not ignore_min_mem:
        print("Kubeflow recommends at least %s GB of memory." % MIN_MEM_GB)
        print("Use `--ignore-min-mem` if you'd like to proceed anyways.")
        sys.exit(1)

    try:
        juju("show-controller", "uk8s", die=False, stdout=False)
    except subprocess.CalledProcessError:
        pass
    else:
        print("Kubeflow has already been enabled.")
        sys.exit(1)

    # Allow specifying the bundle as one of the main types of kubeflow bundles
    # that we create in the charm store, namely full, lite, or edge. The user
    # shoudn't have to specify a version for those bundles. However, allow the
    # user to specify a full charm store URL if they'd like, such as
    # `cs:kubeflow-lite-123`.
    if bundle == 'full':
        bundle = 'cs:kubeflow-230'
    elif bundle == 'lite':
        bundle = 'cs:kubeflow-lite-17'
    elif bundle == 'edge':
        bundle = 'cs:kubeflow-edge-16'
    else:
        bundle = bundle

    run("microk8s-status.wrapper", "--wait-ready", debug=debug)
    run(
        'microk8s-kubectl.wrapper',
        '-nkube-system',
        'rollout',
        'status',
        'deployment.apps/calico-kube-controllers',
        debug=debug,
    )

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
    run(
        'microk8s-kubectl.wrapper',
        '-nkube-system',
        'rollout',
        'status',
        'ds/calico-node',
        debug=debug,
    )

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

    print("DNS and storage setup complete. Checking connectivity...")

    check_connectivity()

    print("Bootstrapping...")
    if no_proxy is not None:
        juju("bootstrap", "microk8s", "uk8s", "--config=juju-no-proxy=%s" % no_proxy)
        juju("add-model", "kubeflow", "microk8s")
        juju("model-config", "-m", "kubeflow", "juju-no-proxy=%s" % no_proxy)
    else:
        juju("bootstrap", "microk8s", "uk8s")
        juju("add-model", "kubeflow", "microk8s")
    print("Bootstrap complete.")

    print("Successfully bootstrapped, deploying...")
    juju("deploy", bundle, "--channel", channel)

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

    if kubectl_exists('service/pipelines-api'):
        with tempfile.NamedTemporaryFile(mode='w+') as f:
            json.dump(
                {
                    'apiVersion': 'v1',
                    'kind': 'Service',
                    'metadata': {'labels': {'juju-app': 'pipelines-api'}, 'name': 'ml-pipeline'},
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

    hostname = parse_hostname(hostname or get_hostname())

    if kubectl_exists('service/dex-auth'):
        juju("config", "dex-auth", "public-url=%s" % hostname.geturl())

    if kubectl_exists('service/oidc-gatekeeper'):
        juju("config", "oidc-gatekeeper", "public-url=%s" % hostname.geturl())

    retry_run(
        "microk8s-kubectl.wrapper",
        "wait",
        "--namespace=kubeflow",
        "--for=condition=Ready",
        "pod",
        "--timeout=30s",
        "--all",
        debug=debug,
        times=100,
    )

    print("Congratulations, Kubeflow is now available.")

    if kubectl_exists('service/istio-ingressgateway'):
        print(
            textwrap.dedent(
                """
        The dashboard is available at %s

            Username: admin
            Password: %s

        To see these values again, run:

            microk8s juju config dex-auth static-username
            microk8s juju config dex-auth static-password

        """
                % (hostname.geturl(), password)
            )
        )
    else:
        print("\nYou have deployed the edge bundle.")
        print("For more information on how to use Kubeflow, see https://www.kubeflow.org/docs/")

    print(
        textwrap.dedent(
            """
        To tear down Kubeflow and associated infrastructure, run:

            microk8s disable kubeflow
    """
        )
    )


if __name__ == "__main__":
    kubeflow(prog_name='microk8s enable kubeflow', auto_envvar_prefix='KUBEFLOW')
