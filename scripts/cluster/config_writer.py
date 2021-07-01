#!/usr/bin/env python3


import click
import os
import yaml
import re
import shutil
from common.utils import (
    try_set_file_permissions,
)


def render(src, dst):
    with open(src, 'r') as template:
        lines = template.read()
        config_lines = lines.replace("$SNAP_DATA", os.environ['SNAP_DATA'])
        config_lines = config_lines.replace("$SNAP_COMMON", os.environ['SNAP_COMMON'])
        with open(dst, 'w') as config:
            config.write(config_lines)


def transcribe(arg, yaml):

    arg = arg.strip()
    # --fail-swap-on has been deprecated, This parameter should be set via the config file
    if arg.startswith("--fail-swap-on"):
        yaml['failSwapOn'] = arg.strip().endswith('rue')
        return "#{}".format(arg)

    # --address has been deprecated, This flag has no effect now and will be removed in v1.24.
    if arg.startswith("--address"):
        return "#{}".format(arg)

    # --anonymous-auth has been deprecated, This parameter should be set via the config file
    if arg.startswith("--anonymous-auth"):
        if "authentication" not in yaml:
            yaml['authentication'] = {}
        if "anonymous" not in yaml['authentication']:
            yaml['authentication']['anonymous'] = {}
        yaml['authentication']['anonymous']['enabled'] = arg.strip().endswith('rue')
        return "#{}".format(arg)

    # --authentication-token-webhook has been deprecated, This parameter should be set via the config file
    if arg.startswith("--authentication-token-webhook"):
        if "authentication" not in yaml:
            yaml['authentication'] = {}
        if "webhook" not in yaml['authentication']:
            yaml['authentication']['webhook'] = {}
        yaml['authentication']['webhook']['enabled'] = arg.strip().endswith('rue')
        return "#{}".format(arg)

    # --client-ca-file has been deprecated, This parameter should be set via the config file
    if arg.startswith("--client-ca-file"):
        if "authentication" not in yaml:
            yaml['authentication'] = {}
        if "webhook" not in yaml['authentication']:
            yaml['authentication']['x509'] = {}
        arg_parts = re.split('=| ', arg, maxsplit=1)
        yaml['authentication']['x509']['clientCAFile'] = arg_parts[1].strip()
        return "#{}".format(arg)

    # --feature-gates has been deprecated, This parameter should be set via the config file
    if arg.startswith("--feature-gates"):
        if "featureGates" not in yaml:
            yaml['featureGates'] = {}
        fg_line = re.split('=| ', arg, maxsplit=1)[-1]
        fg_line = fg_line.strip('"')
        fg_list = fg_line.split(',')
        for fg in fg_list:
            fg_parts = fg.split('=')
            yaml['featureGates'][fg_parts[0]] = fg_parts[1].strip().endswith('rue')
        return "#{}".format(arg)

    # --feature-gates has been deprecated, This parameter should be set via the config file
    if arg.startswith("--feature-gates"):
        if "featureGates" not in yaml:
            yaml['featureGates'] = {}
        fg_line = re.split('=| ', arg, maxsplit=1)[-1]
        fg_line = fg_line.strip('"')
        fg_list = fg_line.split(',')
        for fg in fg_list:
            fg_parts = fg.split('=')
            yaml['featureGates'][fg_parts[0]] = fg_parts[1].strip().endswith('rue')
        return "#{}".format(arg)

    # --eviction-hard has been deprecated, This parameter should be set via the config file
    if arg.startswith("--eviction-hard"):
        if "evictionHard" not in yaml:
            yaml['evictionHard'] = {}
        ev_line = re.split('=| ', arg, maxsplit=1)[-1]
        click.echo(ev_line)
        ev_line = ev_line.strip('"')
        click.echo(ev_line)
        ev_list = ev_line.split(',')
        for ev in ev_list:
            ev_parts = ev.split('<')
            yaml['evictionHard'][ev_parts[0]] = ev_parts[1].strip()
        return "#{}".format(arg)


    # Any other argument
    return arg


def migrate(src, dst):
    if not os.path.exists(dst):
        open(dst, 'a').close()
        try_set_file_permissions(dst)

    src_tmp = "{}.tmp".format(src)
    with open(dst, 'w+') as config_file:
        config_yaml = yaml.safe_load(config_file)
        if config_yaml == None:
            config_yaml = {}
        config_yaml['kind'] = "KubeletConfiguration"
        config_yaml['apiVersion'] = "kubelet.config.k8s.io/v1beta1"
        with open(src, 'r') as args_fp:
            args = args_fp.readlines()
            with open(src_tmp, 'w') as new_args_fp:
                for arg in args:
                    new_arg = transcribe(arg, config_yaml)
                    new_args_fp.write(new_arg)
        yaml.dump(config_yaml, config_file)

    try_set_file_permissions(src_tmp)
    shutil.move(src_tmp, src)


@click.command()
@click.argument("mode", required=True)
@click.argument('src', type=click.Path(exists=True))
@click.argument('dst')
def config_writer(mode, src, dst):
    """Write a yaml config or a config template based on the mode of operation.

    The two modes are:

    - "migrate": we read from src an old style arguments and we coments out the ones
    not valid anymore. We move the arguments to the a yaml file that acts as a configs tempalte.
    Config templates have environment variables such as $SNAP_DATA.

    - "render": renders a template config file (yaml file that includes env virables) to
    config yaml files ready to be used byKubernetes services.
    """

    if mode == "migrate":
        click.echo("Migrating arguments from {} to template yaml {}.".format(src, dst))
        migrate(src, dst)
    elif mode == "render":
        click.echo("Rendering config tempalte yaml file {} to config yaml {}.".format(src, dst))
        render(src, dst)
    else:
        click.echo("Unsoported mode {}.".format(mode))
        exit(1)


if __name__ == '__main__':
    config_writer()
