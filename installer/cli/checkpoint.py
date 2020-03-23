import os
import pickle
from datetime import datetime
from vm_providers.factory import get_provider_for


CHECKPOINT_FILE = '.microk8s.checkpoint'
CHECKPOINT_PATH = os.path.join(os.path.expanduser('~'), CHECKPOINT_FILE)
ALIAS_FILE = '.microk8s.rc'
ALIAS_PATH = os.path.join(os.path.expanduser('~'), ALIAS_FILE)


def sync(force: bool = False) -> None:
    """
    Synchronise the alias file with the available commands.

    :return: None
    """
    if not _check_checkpoint() or force:
        _sync_commands()
        _make_checkpoint()


def _sync_commands() -> None:
    """
    Rewrite the alias file.

    :return: None
    """
    if platform in ['linux', 'darwin']:
        with open(ALIAS_PATH, 'w') as f:
            for i in _get_microk8s_commands():
                f.write('alias microk8s.{0}="microk8s {0}"'.format(i))
    elif platform in ['win32']:
        with open(ALIAS_PATH, 'w') as f:
            for i in _get_microk8s_commands():
                f.write('doskey microk8s.{0}=microk8s {0}'.format(i))


def _make_checkpoint() -> None:
    """
    Stamp a current timestamp into the checkpoint file.

    :return: None
    """
    with open(CHECKPOINT_PATH, 'w') as f:
        pickle.dump(datetime.now(), f)


def _check_checkpoint() -> bool:
    """
    Run this every time.  We're trying to keep the aliases in sync with the underlying CLI.

    :return: Boolean true if okay false if outdated.
    """
    if os.path.isfile(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            previous = pickle.load(f)
    
        if (datetime.now() - previous).days > 30:
            return False
        
        return True

    return False


def get_microk8s_commands() -> List:
    """
    Pull the MicroK8s commands from the VM.

    :return: List String
    """
    vm_provider_name = "multipass"
    vm_provider_class = get_provider_for(vm_provider_name)
    echo = Echo()
    try:
        vm_provider_class.ensure_provider()
        instance = vm_provider_class(echoer=echo)
        instance_info = instance.get_instance_info()
        if instance_info.is_running():
            commands = instance.run('ls -1 /snap/bin/'.split(), hide_output=True)
            mk8s = [c.decode().replace('microk8s.', '') for c in commands.split() if c.decode().startswith('microk8s')]
            return mk8s
