import click
import os
import subprocess
from dateutil.parser import parse
import datetime

#snapdata_path = os.environ.get('SNAP_DATA')
#snap_path = os.environ.get('SNAP')
snapdata_path = '/var/snap/microk8s/current/'
snap_path = '/snap/microk8s/current/'
backup_dir = '{}/var/log/ca-backup/'.format(snapdata_path)


def check_certificate():
    cmd = "{}/usr/bin/openssl x509 -enddate -noout -in {}/certs/ca.crt".format(snap_path, snapdata_path)
    try:
        cert_expire = subprocess.check_output(cmd.split())
        cert_expire_date = cert_expire.decode().split('=')
        date = parse(cert_expire_date[1])
        diff = date - datetime.datetime.now(datetime.timezone.utc)
        click.echo('The CA certificate will expire in {} days.'.format(diff.days))
    except subprocess.CalledProcessError as e:
        click.echo('Failed to get CA info. {}'.format(e))
        exit(4)


def undo_refresh():
    if not os.path.exists(backup_dir):
        click.echo('No previous backup found')
        exit(1)

    try:
        subprocess.check_call('cp -r {}/certs {}/'.format(backup_dir, snapdata_path).split())
        subprocess.check_call('cp -r {}/credentials {}'.format(backup_dir, snapdata_path).split())
    except subprocess.CalledProcessError as e:
        click.echo('Failed to recover certificates')
        exit(4)

    try:
        subprocess.check_call('{}/microk8s-stop.wrapper'.format(snap_path).split())
    except:
        pass

    try:
        subprocess.check_call('{}/microk8s-start.wrapper'.format(snap_path).split())
    except subprocess.CalledProcessError as e:
        click.echo('Failed to start MicroK8s after reverting the certificates')
        exit(4)


def update_configs():
    subprocess.Popen(['bash', '-c', '. {}/actions/common/utils.sh; update_configs'.format(snap_path)])


def take_backup():
    try:
        subprocess.check_call('mkdir -p {}'.format(backup_dir).split())
        subprocess.check_call('cp -r {}/certs {}'.format(snapdata_path, backup_dir).split())
        subprocess.check_call('cp -r {}/credentials {}'.format(snapdata_path, backup_dir).split())
    except subprocess.CalledProcessError as e:
        click.echo('Failed to backup the current CA. {}'.format(e))
        exit(10)


def produce_certs():
    subprocess.check_call('rm -rf {}/certs/ca.crt'.format(snapdata_path).split())
    subprocess.check_call('rm -rf {}/certs/front-proxy-ca.crt'.format(snapdata_path).split())
    subprocess.check_call('rm -rf {}/certs/csr.conf'.format(snapdata_path).split())
    subprocess.Popen(['bash', '-c', '. {}/actions/common/utils.sh; produce_certs'.format(snap_path)])
    subprocess.check_call('rm -rf .slr'.split())


def refresh_ca():
    click.echo("Taking a backup of the current certificates under {}".format(backup_dir))
    take_backup()
    click.echo("Creating new certificates")
    try:
        produce_certs()
    except subprocess.CalledProcessError as e:
        click.echo("Failed to produce new certificates. Reverting.")
        undo_refresh()
        exit(20)
    click.echo("Creating new kubeconfig file")
    update_configs()
    msg = """
The CA certificates have been replaced. Kubernetes will restart the pods of your workloads.
Any worker nodes you may have in your cluster need to be removed and re-joined to become aware of the new CA.
"""
    click.echo(msg)


def install_certs(ca_dir):
    subprocess.check_call('cp {}/ca.crt {}/certs/'.format(ca_dir, snapdata_path).split())
    subprocess.check_call('cp {}/ca.key {}/certs/'.format(ca_dir, snapdata_path).split())
    subprocess.Popen(['bash', '-c', '. {}/actions/common/utils.sh; gen_server_cert'.format(snap_path)])


def validate_certificates(ca_dir):
    pass


def install_ca(ca_dir):
    click.echo("Validating provided certificates")
    validate_certificates(ca_dir)
    click.echo("Taking a backup of the current certificates under {}".format(backup_dir))
    take_backup()
    click.echo("Installing provided certificates")
    try:
        install_certs(ca_dir)
    except subprocess.CalledProcessError as e:
        click.echo("Failed to produce new certificates. Reverting.")
        undo_refresh()
        exit(20)
    click.echo("Creating new kubeconfig file")
    update_configs()
    msg = """
    The CA certificates have been replaced. Kubernetes will restart the pods of your workloads.
    Any worker nodes you may have in your cluster need to be removed and re-joined to become aware of the new CA.
    """
    click.echo(msg)


@click.command(
    name='refresh-certs',
    help='Replace the CA certificates with the ca.crt and ca.key found in CA_DIR.\n'
         'Omit the CA_DIR to auto-generate a new CA.'
)
@click.argument(
    'ca_dir',
    required=False,
    default=None,
    type=click.Path(exists=True)
)
@click.option(
    '-u',
    '--undo',
    is_flag=True,
    default=False,
    help='Revert the last refresh performed'
)
@click.option(
    '-c',
    '--check',
    is_flag=True,
    default=False,
    help='Check the expiration time of the installed CA'
)
@click.option(
    '--help',
    is_flag=True,
    default=False,
)
def refresh_certs(ca_dir, undo, check, help):
    if help:
        show_help()
        exit(0)

    if not ca_dir is None and (undo or check):
        click.echo("Please do not set any options in combination with the CA_DIR.")
        exit(1)

    if undo and check:
        click.echo("Please select either one of the options -c or -u, not both.")
        exit(2)

    if check:
        check_certificate()
        exit(0)

    if undo:
        undo_refresh()
        exit(0)

    if not ca_dir:
        refresh_ca()
    else:
        install_ca(ca_dir)

    print(ca_dir, undo, check)


def show_help():
    msg = """Usage: microk8s refresh-certs [OPTIONS] [CA_DIR]

  Replace the CA certificates with the ca.crt and ca.key found in CA_DIR.
  Omit the CA_DIR argument to auto-generate a new CA.

Options:
  -u, --undo   Revert the last refresh performed
  -c, --check  Check the expiration time of the installed CA
  --help       Show this message and exit."""
    click.echo(msg)


if __name__ == '__main__':
    refresh_certs()