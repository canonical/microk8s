#!/usr/bin/python3
import click
import os
import subprocess
from dateutil.parser import parse
import datetime

from common.utils import (
    exit_if_no_root,
)

from common.cluster.utils import (
    is_token_auth_enabled,
    rebuild_x509_auth_client_configs,
)

snapdata_path = os.environ.get("SNAP_DATA")
snap_path = os.environ.get("SNAP")
backup_dir = "{}/certs-backup/".format(snapdata_path)

certs = {
    "ca.crt": "CA",
    "server.crt": "server",
    "front-proxy-client.crt": "front proxy client",
}


def check_certificate():
    """
    Print the days until the current certificate expires
    """
    try:
        for file in certs.keys():
            cmd = "{}/openssl.wrapper x509 -enddate -noout -in {}/certs/{}".format(
                snap_path, snapdata_path, file
            )
            cert_expire = subprocess.check_output(cmd.split())
            cert_expire_date = cert_expire.decode().split("=")
            date = parse(cert_expire_date[1])
            diff = date - datetime.datetime.now(datetime.timezone.utc)
            click.echo("The {} certificate will expire in {} days.".format(certs[file], diff.days))
    except subprocess.CalledProcessError as e:
        click.echo("Failed to get certificate info. {}".format(e))
        exit(4)


def undo_refresh():
    """
    Revert last certificate operation
    """
    if not os.path.exists(backup_dir):
        click.echo("No previous backup found")
        exit(1)

    try:
        subprocess.check_call("cp -r {}/certs {}/".format(backup_dir, snapdata_path).split())
        subprocess.check_call("cp -r {}/credentials {}".format(backup_dir, snapdata_path).split())
    except subprocess.CalledProcessError:
        click.echo("Failed to recover certificates")
        exit(4)

    restart()


def restart(service="all"):
    """Restart microk8s services"""
    if service == "all":
        click.echo("Restarting, please wait.")
        try:
            subprocess.check_call("{}/microk8s-stop.wrapper".format(snap_path).split())
        except subprocess.CalledProcessError:
            pass

        try:
            subprocess.check_call("{}/microk8s-start.wrapper".format(snap_path).split())
        except subprocess.CalledProcessError:
            click.echo("Failed to start MicroK8s after reverting the certificates")
            exit(4)
    else:
        click.echo("Restarting service {}.".format(service))
        try:
            subprocess.check_call("snapctl restart microk8s.daemon-{}".format(service).split())
        except subprocess.CalledProcessError:
            click.echo("Failed to restart service microk8s.daemon-{}.".format(service))
            exit(4)


def update_configs():
    """
    Update all kubeconfig files used by the client and the services
    """
    if is_token_auth_enabled():
        p = subprocess.Popen(
            ["bash", "-c", ". {}/actions/common/utils.sh; update_configs".format(snap_path)]
        )
        p.communicate()
    else:
        rebuild_x509_auth_client_configs()
        restart("kubelite")
        restart("cluster-agent")


def take_backup():
    """
    Backup the current certificates and credentials
    """
    try:
        subprocess.check_call("mkdir -p {}".format(backup_dir).split())
        subprocess.check_call("cp -r {}/certs {}".format(snapdata_path, backup_dir).split())
        subprocess.check_call("cp -r {}/credentials {}".format(snapdata_path, backup_dir).split())
    except subprocess.CalledProcessError as e:
        click.echo("Failed to backup the current CA. {}".format(e))
        exit(10)


def reproduce_all_root_ca_certs():
    """
    Produce the CA and the rest of the needed certificates (eg service, front-proxy)
    """
    subprocess.check_call("rm -rf {}/certs/ca.crt".format(snapdata_path).split())
    subprocess.check_call("rm -rf {}/certs/csr.conf".format(snapdata_path).split())
    p = subprocess.Popen(
        ["bash", "-c", ". {}/actions/common/utils.sh; produce_certs".format(snap_path)]
    )
    p.communicate()
    subprocess.check_call("rm -rf .slr".split())
    click.echo("Creating new kubeconfig file")
    update_configs()
    msg = """
The CA certificates have been replaced. Kubernetes will restart the pods of your workloads.
Any worker nodes you may have in your cluster need to be removed and \
re-joined to become aware of the new CA.
"""
    click.echo(msg)


def reproduce_front_proxy_client_cert():
    """
    Produce the front proxy client certificate
    """
    subprocess.check_call("rm -rf {}/certs/front-proxy-client.crt".format(snapdata_path).split())
    subprocess.check_call(
        [
            "bash",
            "-c",
            ". {}/actions/common/utils.sh; refresh_csr_conf; gen_proxy_client_cert".format(
                snap_path
            ),
        ]
    )
    subprocess.check_call("rm -rf .slr".split())
    restart("kubelite")


def reproduce_server_cert():
    """
    Produce the server certificate
    """
    subprocess.check_call("rm -rf {}/certs/server.crt".format(snapdata_path).split())
    subprocess.check_call(
        [
            "bash",
            "-c",
            ". {}/actions/common/utils.sh; refresh_csr_conf; gen_server_cert".format(snap_path),
        ]
    )
    subprocess.check_call("rm -rf .slr".split())
    restart("kubelite")
    restart("cluster-agent")


def refresh_cert(cert):
    """
    Refresh the selected certificate with an autogenerated CA
    """
    click.echo("Taking a backup of the current certificates under {}".format(backup_dir))
    take_backup()
    try:
        click.echo("Creating new certificates")
        if cert == "ca.crt":
            reproduce_all_root_ca_certs()
        elif cert == "server.crt":
            reproduce_server_cert()
        elif cert == "front-proxy-client.crt":
            reproduce_front_proxy_client_cert()
        else:
            # this should never happen
            click.echo("Unknown certificate to refresh")
    except subprocess.CalledProcessError:
        click.echo("Failed to produce new certificates. Reverting.")
        undo_refresh()
        exit(20)


def install_certs(ca_dir):
    """
    Recreate service certificate and front proxy using a user provided CA
    :param ca_dir: path to the ca.crt and ca.key
    """
    subprocess.check_call("cp {}/ca.crt {}/certs/".format(ca_dir, snapdata_path).split())
    subprocess.check_call("cp {}/ca.key {}/certs/".format(ca_dir, snapdata_path).split())
    p = subprocess.Popen(
        ["bash", "-c", ". {}/actions/common/utils.sh; gen_server_cert".format(snap_path)]
    )
    p.communicate()


def validate_certificates(ca_dir):
    """
    Perform some basic testing of the user provided CA
    :param ca_dir: path to the ca.crt and ca.key
    """
    if not os.path.isfile("{}/ca.crt".format(ca_dir)) or not os.path.isfile(
        "{}/ca.key".format(ca_dir)
    ):
        click.echo("Could not find ca.crt and ca.key files in {}".format(ca_dir))
        exit(30)

    try:
        cmd = "{}/openssl.wrapper rsa -in {}/ca.key -check -noout -out /dev/null".format(
            snap_path, ca_dir
        )
        subprocess.check_call(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        click.echo("CA private key is invalid. {}".format(e))
        exit(31)

    try:
        cmd = "{}/openssl.wrapper x509 -in {}/ca.crt -text -noout -out /dev/null".format(
            snap_path, ca_dir
        )
        subprocess.check_call(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        click.echo("CA certificate is invalid. {}".format(e))
        exit(32)


def install_ca(ca_dir):
    """
    Install the user provided CA
    :param ca_dir: path to the user provided CA files
    """
    click.echo("Validating provided certificates")
    validate_certificates(ca_dir)
    click.echo("Taking a backup of the current certificates under {}".format(backup_dir))
    take_backup()
    click.echo("Installing provided certificates")
    try:
        install_certs(ca_dir)
    except subprocess.CalledProcessError:
        click.echo("Failed to produce new certificates. Reverting.")
        undo_refresh()
        exit(20)
    click.echo("Creating new kubeconfig file")
    update_configs()
    msg = """
    The CA certificates have been replaced. Kubernetes will restart the pods of your workloads.
    Any worker nodes you may have in your cluster need to be removed and re-joined to become
    aware of the new CA.
    """
    click.echo(msg)


@click.command(
    name="refresh-certs",
    help="Autogenerate a certificate or replace the root CA with the one found in CA_DIR.\n"
    "Omit the CA_DIR and use the --cert flag to autogenerate a new certificate.",
)
@click.argument("ca_dir", required=False, default=None, type=click.Path(exists=True))
@click.option("-u", "--undo", is_flag=True, default=False, help="Revert the last refresh performed")
@click.option(
    "-c",
    "--check",
    is_flag=True,
    default=False,
    help="Check the expiration time of the installed CA",
)
@click.option(
    "-e",
    "--cert",
    type=click.Choice(certs.keys()),
    help="The certificate to be autogenerated",
)
@click.option(
    "-h",
    "--help",
    is_flag=True,
    default=False,
)
def refresh_certs(ca_dir, undo, check, cert, help):
    if help:
        show_help()
        exit(0)

    if ca_dir is not None and (undo or check or cert):
        click.echo("Please do not set any options in combination with the CA_DIR.")
        exit(1)

    operations_selected = 0
    for op in [undo, check, cert]:
        if op:
            operations_selected += 1
    if operations_selected > 1:
        click.echo("Please select only one of the options -c, -u or -e.")
        exit(2)

    # Operations here will need root privileges as some of the credentials
    # and certificates are used by system services.
    exit_if_no_root()
    if check:
        check_certificate()
        exit(0)

    if undo:
        undo_refresh()
        exit(0)

    if not ca_dir:
        if not cert:
            click.echo("Please use the '--cert' flag to select the certificate you need refreshed.")
            click.echo("")
            click.echo("Available certificate options:")
            click.echo("'server.crt': refreshes the server certificate")
            click.echo("'front-proxy-client.crt': refreshes the front proxy client certificate")
            click.echo("'ca.crt': refreshes the root CA and all certificates created from it.")
            click.echo(
                "            Warning: refreshing the root CA requires nodes to leave and re-join the cluster"
            )
            exit(3)
        else:
            refresh_cert(cert)
    else:
        install_ca(ca_dir)


def show_help():
    msg = """Usage: microk8s refresh-certs [OPTIONS] [CA_DIR]

  Replace the CA certificates with the ca.crt and ca.key found in CA_DIR.
  Omit the CA_DIR argument and use the '--cert' flag to auto-generate a new CA
  or any other certificate.

Options:
  -c, --check  Check the expiration time of the installed certificates
  -e, --cert   The certificate to be autogenerated, must be one of {}
  -u, --undo   Revert the last refresh performed
  -h, --help       Show this message and exit."""
    click.echo(msg.format(list(certs.keys())))


if __name__ == "__main__":
    refresh_certs()
