#!/usr/bin/python3
import os
import re
import yaml


def patch_line(line):
    """
    Patch an individual line.

    :return: Any
    """
    line = line.replace("v3.19.1", "v3.19.3")
    line = line.replace("v3.17.3", "v3.19.3")
    return line


def patch_document(document):
    """
    Traverse the document and replace any references to old Calico image versions.

    :return: None
    """
    for k, v in document.items():
        if type(v) is dict:
            patch_document(v)
        elif type(v) is list:
            for i in range(len(v)):
                if type(v[i]) is dict:
                    patch_document(v[i])
                elif type(v[i]) is str:
                    v[i] = patch_line(v[i])
            document[k] = v
        elif type(v) is str:
            document[k] = patch_line(v)


def main():
    """
    Run the upgrade.

    :return: None
    """
    path = os.path.expandvars("${SNAP_DATA}/args/cni-network/cni.yaml")
    modified = []

    with open(path, "r") as f:
        for document in yaml.safe_load_all(f):
            if document:
                patch_document(document)
                modified.append(document)

    with open(path, "w") as f:
        yaml.dump_all(modified, f)


if __name__ == "__main__":
    main()
