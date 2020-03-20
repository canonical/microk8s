import sys
from cli.microk8s import cli


def main():
    """
    Create parity between Linux and other platforms by
    handling the '.' to split subcomands.

    :returns: None
    """
    split = sys.argv[0].split('microk8s.')
    new_argv = [split[0] + 'microk8s', split[1]]

    if len(sys.argv) > 1:
        new_argv += sys.argv[1:]

    sys.argv = new_argv

    cli()
