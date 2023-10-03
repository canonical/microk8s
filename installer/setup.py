from setuptools import setup

setup(
    name="microk8s",
    version="1.0.2",
    url="https://github.com/canonical/microk8s",
    license="Apache-2.0",
    author="Joe Borg",
    author_email="joseph.borg@canonical.com",
    description="MicroK8s is a small, fast, single-package Kubernetes for developers, IoT and edge",
    packages=["cli", "common", "vm_providers", "vm_providers._multipass", "vm_providers.repo"],
    install_requires=[
        "click~=7.0",
        "progressbar33==2.4",
        "requests==2.25.1",
        "requests_unixsocket==0.1.5",
        "simplejson==3.8.2",
        "toml==0.10.0",
        "urllib3==1.26.17",
    ],
    platforms="any",
    entry_points={
        "console_scripts": [
            "microk8s=cli.microk8s:cli",
        ]
    },
)
