#!/usr/bin/env python3
import shutil
import toml
import os

"""
This is a helper script to migrate registry configurations from version 1 to version2.
Also include the custom sandbox_image 'k8s.gcr.io/pause:3.1' to those who dont have access to k8s.gcr.io.

"""


# if the file is not in version2, we do the migration.

def needs_migration(templatefileBackup):
    with open(templatefileBackup) as f:
        if 'version = 2' in f.read():
            return False
    
    return True

def get_sandbox_image(config):
    with open(config) as file:
        for line in file:
            if "sandbox_image" in line:
                matchedLine = line
                return matchedLine

def replace_sandbox_image(config, original_sandbox_image):
    fin = open(config, "rt")
    data = fin.read()
    data = data.replace('sandbox_image = "k8s.gcr.io/pause:3.1"', original_sandbox_image)
    fin.close()
    fin = open(config, "wt")
    fin.write(data)
    fin.close()

def extract_custom_registry(config):
    registryToml = "\n"
    configv1 = toml.load(open(templatefileBackup))
    for k,v in configv1["plugins"]["cri"]["registry"]["mirrors"].items():
        if (k != "docker.io") and (k != "localhost:32000"):
            registryToml = registryToml + "[plugins.\"io.containerd.grpc.v1.cri\".registry.mirrors.\"" +  k + "\"]\n"
            registryToml = registryToml + toml.dumps(v) + "\n"
    
    return registryToml



snap = os.environ.get('SNAP')
snap_data = os.environ.get('SNAP_DATA')
templatefile = snap_data +"/args/"+ "containerd-template.toml"
templatefileBackup = templatefile + ".backup"
customRegistryPath = snap_data + "/args/" + "containerd-custom/"
configv2 = snap + "/default-args/containerd-template.toml"


if needs_migration(templatefile):
    shutil.copyfile(os.path.realpath(templatefile), os.path.realpath(templatefileBackup))
    print ("Migrating the configuration.")

    shutil.copyfile(configv2, templatefile)
    registryv2File = open(templatefile, "a")

    registryv2File.write(extract_custom_registry(templatefileBackup))
    registryv2File.close()

    sandboxImage = get_sandbox_image(templatefileBackup)

    replace_sandbox_image(templatefile, sandboxImage)
    
    print ("Migration done.")