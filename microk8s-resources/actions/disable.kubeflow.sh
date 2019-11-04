#!/usr/bin/env python3

import os
import subprocess
import sys


def main():
    env = os.environ.copy()
    env["PATH"] += ":%s" % os.environ["SNAP"]

    try:
        subprocess.run(
            ["microk8s-juju.wrapper", "show-controller", "uk8s"],
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        print("Kubeflow is already disabled.")
        sys.exit(0)

    print("Disabling Kubeflow...")

    subprocess.run(
        [
            "microk8s-juju.wrapper",
            "destroy-controller",
            "-y",
            "uk8s",
            "--destroy-all-models",
            "--destroy-storage",
        ],
        env=env,
    )


if __name__ == "__main__":
    main()
