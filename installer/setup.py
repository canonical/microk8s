from setuptools import setup

setup(
    name='microk8s',
    version='1.0.0',
    url='https://github.com/ubuntu/microk8s',
    license='Apache-2.0',
    author='Joe Borg',
    author_email='joseph.borg@canonical.com',
    description='MicroK8s is a small, fast, single-package Kubernetes for developers, IoT and edge.',
    packages=[
        'cli',
        'common',
        'vm_providers',
        'vm_providers._multipass',
        'vm_providers.repo'
    ],
    install_requires=[
        'setuptools',
        'click~=7.0',
        'jsonschema==2.5.1',
        'progressbar33==2.4',
        'requests==2.20.0',
        'requests_unixsocket==0.1.5',
        'simplejson==3.8.2',
        'toml==0.10.0',
        'wheel'
    ],
    platforms='any',
    entry_points={'console_scripts': [
        'microk8s=cli.microk8s:cli',
        'microk8s.add-node=cli.parity:main',
        'microk8s.cilium=cli.parity:main',
        'microk8s.config=cli.parity:main',
        'microk8s.ctr=cli.parity:main',
        'microk8s.disable=cli.parity:main',
        'microk8s.enable=cli.parity:main',
        'microk8s.helm=cli.parity:main',
        'microk8s.helm3=cli.parity:main',
        'microk8s.inspect=cli.parity:main',
        'microk8s.istioctl=cli.parity:main',
        'microk8s.join=cli.parity:main',
        'microk8s.juju=cli.parity:main',
        'microk8s.kubectl=cli.parity:main',
        'microk8s.leave=cli.parity:main',
        'microk8s.linkerd=cli.parity:main',
        'microk8s.remove-node=cli.parity:main',
        'microk8s.reset=cli.parity:main',
        'microk8s.start=cli.parity:main',
        'microk8s.status=cli.parity:main',
        'microk8s.stop=cli.parity:main'
    ]}
)
