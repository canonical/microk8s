import os.path
import datetime
import time
import yaml
import platform
from subprocess import check_output, CalledProcessError


arch_translate = {'aarch64': 'arm64', 'x86_64': 'amd64'}


def run_until_success(cmd, timeout_insec=60, err_out=None):
    """
    Run a command untill it succeeds or times out.
    Args:
        cmd: Command to run
        timeout_insec: Time out in seconds
        err_out: If command fails and this is the output, return.

    Returns: The string output of the command

    """
    deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_insec)
    while True:
        try:
            output = check_output(cmd.split()).strip().decode('utf8')
            return output.replace('\\n', '\n')
        except CalledProcessError as err:
            output = err.output.strip().decode('utf8').replace('\\n', '\n')
            if output == err_out:
                return output
            if datetime.datetime.now() > deadline:
                raise
            print("Retrying {}".format(cmd))
            time.sleep(3)


def kubectl(cmd, timeout_insec=300, err_out=None):
    """
    Do a kubectl <cmd>
    Args:
        cmd: left part of kubectl <left_part> command
        timeout_insec: timeout for this job
        err_out: If command fails and this is the output, return.

    Returns: the kubectl response in a string

    """
    cmd = '/snap/bin/microk8s.kubectl ' + cmd
    return run_until_success(cmd, timeout_insec, err_out)


def docker(cmd):
    """
    Do a docker <cmd>
    Args:
        cmd: left part of docker <left_part> command

    Returns: the docker response in a string

    """
    docker_bin = '/usr/bin/docker'
    if os.path.isfile('/snap/bin/microk8s.docker'):
        docker_bin = '/snap/bin/microk8s.docker'
    cmd = docker_bin + ' ' + cmd
    return run_until_success(cmd)


def kubectl_get(target, timeout_insec=300):
    """
    Do a kubectl get and return the results in a yaml structure.
    Args:
        target: which resource we are getting
        timeout_insec: timeout for this job

    Returns: YAML structured response

    """
    cmd = 'get -o yaml ' + target
    output = kubectl(cmd, timeout_insec)
    return yaml.load(output)


def wait_for_pod_state(
    pod, namespace, desired_state, desired_reason=None, label=None, timeout_insec=600
):
    """
    Wait for a a pod state. If you do not specify a pod name and you set instead a label
    only the first pod will be checked.
    """
    deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_insec)
    while True:
        if datetime.datetime.now() > deadline:
            raise TimeoutError(
                "Pod {} not in {} after {} seconds.".format(pod, desired_state, timeout_insec)
            )
        cmd = 'po {} -n {}'.format(pod, namespace)
        if label:
            cmd += ' -l {}'.format(label)
        data = kubectl_get(cmd, timeout_insec)
        if pod == "":
            if len(data['items']) > 0:
                status = data['items'][0]['status']
            else:
                status = []
        else:
            status = data['status']
        if 'containerStatuses' in status:
            container_status = status['containerStatuses'][0]
            state, details = list(container_status['state'].items())[0]
            if desired_reason:
                reason = details.get('reason')
                if state == desired_state and reason == desired_reason:
                    break
            elif state == desired_state:
                break
        time.sleep(3)


def wait_for_installation(cluster_nodes=1):
    """
    Wait for kubernetes service to appear.
    """
    while True:
        cmd = 'svc kubernetes'
        data = kubectl_get(cmd, 300)
        service = data['metadata']['name']
        if 'kubernetes' in service:
            break
        else:
            time.sleep(3)

    while True:
        cmd = 'get no'
        nodes = kubectl(cmd, 300)
        if nodes.count(' Ready') == cluster_nodes:
            break
        else:
            time.sleep(3)

    # Allow rest of the services to come up
    time.sleep(30)


def wait_for_namespace_termination(namespace, timeout_insec=360):
    """
    Wait for the termination of the provided namespace.
    """

    print("Waiting for namespace {} to be removed".format(namespace))
    deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_insec)
    while True:
        try:
            cmd = '/snap/bin/microk8s.kubectl get ns {}'.format(namespace)
            check_output(cmd.split()).strip().decode('utf8')
            print('Waiting...')
        except CalledProcessError:
            if datetime.datetime.now() > deadline:
                raise
            else:
                return
        time.sleep(10)


def microk8s_enable(addon, timeout_insec=300):
    """
    Disable an addon

    Args:
        addon: name of the addon
        timeout_insec: seconds to keep retrying

    """
    # NVidia pre-check so as to not wait for a timeout.
    if addon == 'gpu':
        nv_out = run_until_success("lsmod", timeout_insec=10)
        if "nvidia" not in nv_out:
            print("Not a cuda capable system. Will not test gpu addon")
            raise CalledProcessError(1, "Nothing to do for gpu")

    cmd = '/snap/bin/microk8s.enable {}'.format(addon)
    return run_until_success(cmd, timeout_insec)


def microk8s_disable(addon):
    """
    Enable an addon

    Args:
        addon: name of the addon

    """
    cmd = '/snap/bin/microk8s.disable {}'.format(addon)
    return run_until_success(cmd, timeout_insec=300)


def microk8s_clustering_capable():
    """
    Are we in a clustering capable microk8s?
    """
    return os.path.isfile('/snap/bin/microk8s.join')


def microk8s_reset(cluster_nodes=1):
    """
    Call microk8s reset
    """
    cmd = '/snap/bin/microk8s.reset'
    run_until_success(cmd, timeout_insec=300)
    wait_for_installation(cluster_nodes)


def update_yaml_with_arch(manifest_file):
    """
    Updates any $ARCH entry with the architecture in the manifest

    """
    arch = arch_translate[platform.machine()]
    with open(manifest_file) as f:
        s = f.read()

    with open(manifest_file, 'w') as f:
        s = s.replace('$ARCH', arch)
        f.write(s)
