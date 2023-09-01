#!/usr/bin/env python3

import json
import os
from pathlib import Path
import subprocess
import sys
import yaml

DIR = Path(__file__).absolute().parent

SNAPCRAFT_PART_BUILD = Path(os.getenv("SNAPCRAFT_PART_BUILD", ""))
SNAPCRAFT_PART_INSTALL = Path(os.getenv("SNAPCRAFT_PART_INSTALL", ""))

BUILD_DIRECTORY = SNAPCRAFT_PART_BUILD.exists() and SNAPCRAFT_PART_BUILD or DIR / ".build"
INSTALL_DIRECTORY = SNAPCRAFT_PART_INSTALL.exists() and SNAPCRAFT_PART_INSTALL or DIR / ".install"

# Location of Python binary
PYTHON = INSTALL_DIRECTORY / ".." / ".." / "python-runtime" / "install" / "usr" / "bin" / "python3"

# Location of MicroK8s addons
MICROK8S_ADDONS = INSTALL_DIRECTORY / ".." / ".." / "microk8s-addons" / "install" / "addons"

# List of tools used to build or bundled in the snap
TOOLS = {
    "go": ["go", "version"],
    "gcc": ["gcc", "--version"],
    "python": [PYTHON, "-B", "-VV"],
    "python-requirements": [PYTHON, "-B", "-m", "pip", "freeze"],
}

# Retrieve list of components we care about from the snapcraft.yaml file
with open(DIR / ".." / "snap" / "snapcraft.yaml") as fin:
    COMPONENTS = yaml.safe_load(fin)["parts"]["bom"]["after"]


def _listdir(dir: Path):
    try:
        return sorted(os.listdir(dir))
    except OSError:
        return []


def _parse_output(*args, **kwargs):
    return subprocess.check_output(*args, **kwargs).decode().strip()


def _read_file(path: Path) -> str:
    return path.read_text().strip()


if __name__ == "__main__":
    BOM = {
        "microk8s": {
            "version": _parse_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
            "revision": _parse_output(["git", "rev-parse", "HEAD"]),
        },
        "tools": {},
        "components": {},
        "addons": {},
    }

    for tool_name, version_cmd in TOOLS.items():
        BOM["tools"][tool_name] = _parse_output(version_cmd).split("\n")

    for component in COMPONENTS:
        component_dir = DIR / "components" / component

        try:
            version = _parse_output([component_dir / "version.sh"])
            patches = _parse_output([PYTHON, DIR / "print-patches-for.py", component, version])
            clean_patches = []
            if patches:
                clean_patches = [p[p.find("build-scripts/") :] for p in patches.split("\n")]

            BOM["components"][component] = {
                "repository": _read_file(component_dir / "repository"),
                "version": version,
                "revision": _parse_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=BUILD_DIRECTORY / ".." / ".." / component / "build" / component,
                ),
                "patches": clean_patches,
            }
        except OSError as e:
            print(f"Could not get info for {component}: {e}", file=sys.stderr)

    for repo in _listdir(MICROK8S_ADDONS):
        repo_dir = MICROK8S_ADDONS / repo
        if not repo_dir.is_dir():
            continue

        BOM["addons"][repo] = {
            "repository": _parse_output(["git", "remote", "get-url", "origin"], cwd=repo_dir),
            "version": _parse_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir),
            "revision": _parse_output(["git", "rev-parse", "HEAD"], cwd=repo_dir),
        }

    print(json.dumps(BOM, indent=2))
