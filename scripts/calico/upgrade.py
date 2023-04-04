#!/usr/bin/python3
import os
import yaml
import shutil
import sys


def get_calico_node_spec(cni_file):
    """
    Extract the section of the calico node container

    return: The container section of the calico node, None otherwise
    """
    try:
        with open(cni_file, "r", encoding="utf8") as f:
            for doc in yaml.safe_load_all(f):
                if doc and doc["kind"] == "DaemonSet" and doc["metadata"]["name"] == "calico-node":
                    # Reach for the containers
                    if (
                        doc["spec"]
                        and doc["spec"]["template"]
                        and doc["spec"]["template"]["spec"]
                        and doc["spec"]["template"]["spec"]["containers"]
                    ):
                        containers = doc["spec"]["template"]["spec"]["containers"]
                        for c in containers:
                            if c["name"] == "calico-node":
                                return c
    except (yaml.YAMLError, TypeError) as e:
        print(e, file=sys.stderr)
        return None
    return None


def is_calico_cni_manifest(cni_file):
    """
    Check if this is a Calico CNI manifest

    return: True if the provided manifest is a Calico one, False otherwise
    """
    try:
        with open(cni_file, "r", encoding="utf8") as f:
            for doc in yaml.safe_load_all(f):
                if doc and doc["kind"] == "DaemonSet" and doc["metadata"]["name"] == "calico-node":
                    return True
    except (yaml.YAMLError, TypeError) as e:
        print(e, file=sys.stderr)
        return False
    return False


def get_installed_version_of_calico(cni_file):
    """
    Extract the Calico version in the provided CNI manifest

    return: A string with the version, None otherwise
    """
    try:
        c = get_calico_node_spec(cni_file)
        if c:
            parts = c["image"].split(":")
            return parts[-1]
        else:
            return None
    except (yaml.YAMLError, TypeError) as e:
        print(e, file=sys.stderr)
        return None


def get_calicos_autodetection_method(cni_file):
    """
    Extract the IP autodetection method

    return: A string with the IP autodetection method, None otherwise
    """
    try:
        c = get_calico_node_spec(cni_file)
        if c:
            methods = [i["value"] for i in c["env"] if i["name"] == "IP_AUTODETECTION_METHOD"]
            if len(methods) > 0:
                return methods[0]
            return None
    except (yaml.YAMLError, TypeError) as e:
        print(e, file=sys.stderr)
        return None


def patch_manifest(cni_file, autodetection):
    """
    Patch the CNI manifest with the IP autodetection method provided
    """
    yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str

    def repr_str(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.org_represent_str(data)

    yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)

    try:
        with open(cni_file, "r", encoding="utf8") as f:
            to_remove = []
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if not doc:
                    to_remove.append(doc)
                if doc and doc["kind"] == "DaemonSet" and doc["metadata"]["name"] == "calico-node":
                    # Reach for the containers
                    containers = doc["spec"]["template"]["spec"]["containers"]
                    for c in containers:
                        if c["name"] == "calico-node":
                            env = c["env"]
                            for variable in env:
                                if variable["name"] == "IP_AUTODETECTION_METHOD":
                                    variable["value"] = autodetection

            # remove empty yaml documents
            for d in to_remove:
                docs.remove(d)

        with open(cni_file, "w", encoding="utf8") as fout:
            yaml.safe_dump_all(docs, fout)

    except (yaml.YAMLError, TypeError) as e:
        print(e, file=sys.stderr)


def backup_old_cni(cni_file):
    """
    Creating a backup of the provided file
    """
    backup_cni_file = f"{cni_file}.backup"
    shutil.copyfile(cni_file, backup_cni_file)


def try_upgrade(cni_file, new_cni_file, cni_no_manage=None):
    """
    Perform the upgrade if possible.

    return: True if the CNI needs to be reloaded
    """

    # If cni auto management is disabled by lock file do nothing
    if cni_no_manage is not None and os.path.exists(cni_no_manage):
        return False

    # If cni files are not in place do nothing
    if not (os.path.exists(cni_file) and os.path.exists(new_cni_file)):
        return False

    # If the current cni.yaml is not calico do nothing
    if not is_calico_cni_manifest(cni_file):
        return False

    # If the current cni.yaml is not from 3.21 do nothing
    # s390x will be filtered out because it is in 3.15
    current_version = get_installed_version_of_calico(cni_file)
    if "3.21" not in current_version:
        return False

    backup_old_cni(cni_file)
    autodetection = get_calicos_autodetection_method(cni_file)
    shutil.copyfile(new_cni_file, cni_file)
    if autodetection and "can-reach" in autodetection:
        patch_manifest(cni_file, autodetection)

    return True


def mark_apply_needed(lock_file):
    """
    Remove the lock file provided so the apiserver kicker will re apply the CNI manifest
    """
    try:
        os.remove(lock_file)
    except OSError:
        pass


def main():
    """
    Run the upgrade.

    :return: None
    """
    cni_reapply_lock_file = os.path.expandvars("${SNAP_DATA}/var/lock/cni-loaded")
    cni_file = os.path.expandvars("${SNAP_DATA}/args/cni-network/cni.yaml")
    cni_no_manage = os.path.expandvars("${SNAP_DATA}/var/lock/no-manage-calico")
    new_cni_file = os.path.expandvars(
        "${SNAP}/upgrade-scripts/000-switch-to-calico/resources/calico.yaml"
    )

    if try_upgrade(cni_file, new_cni_file, cni_no_manage):
        # we mark the CNI needs to be updated so the api service kicker will take over
        mark_apply_needed(cni_reapply_lock_file)


if __name__ == "__main__":
    main()
