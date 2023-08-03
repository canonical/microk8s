#!/usr/bin/env python3

import argparse
import os
from pathlib import Path

DIR = Path(__file__).absolute().parent

# SNAPCRAFT_PROJECT_DIR is set when building the snap. If unset, resolve based on current file path
_SNAPCRAFT_PROJECT_DIR = os.getenv("SNAPCRAFT_PROJECT_DIR") or ""
SNAPCRAFT_PROJECT_DIR = _SNAPCRAFT_PROJECT_DIR and Path(_SNAPCRAFT_PROJECT_DIR) or Path(DIR / "..")

STRICT = "confinement: strict" in (SNAPCRAFT_PROJECT_DIR / "snap" / "snapcraft.yaml").read_text()


class Version:
    def __init__(self, version_string: str):
        self.str = version_string
        if version_string[0] == "v":
            version_string = version_string[1:]
        if "-" in version_string:
            version_string = version_string[: version_string.rfind("-")]

        try:
            self.version = [int(x) for x in version_string.split(".")]
            self.type = "semver"
        except (TypeError, ValueError):
            self.version = self.str
            self.type = "string"

    def equal_or_older_than(self, v: "Version") -> bool:
        """Consider the following cases:
        - `v1.1.0` is equal or older than `v1.2.0`.
        - `v1.2.0` is equal or older than `v1.2.0`.
        - `v1.28.0-rc.0` is equal or older than v1.28.0`.
        - `fix/mybug` is not equal or older than `v1.28.0`.
        """
        if self.type == v.type == "semver" and self.version <= v.version:
            return True
        if {self.type, v.type} & {"string"} and v.str.startswith(self.str):
            return True

        return False


def find_suitable_patch_version(candidates: list, target_version: Version) -> str:
    """pick the version string from a list of candidate versions"""
    result = None
    has_default = False
    for candidate in candidates:
        if candidate.str == target_version.str:
            return target_version.str

        has_default = has_default or candidate.str == "default"

        if not candidate.equal_or_older_than(target_version):
            continue

        if result is None or result.equal_or_older_than(candidate):
            result = candidate

    # found a suitable patch directory
    if result:
        return result.str

    # no suitable patch directory found, but there is a default
    if has_default:
        return "default"

    # component does not have any patches
    return None


def get_patches_for(component: str, version_string: str, strict: bool) -> list:
    """Return a list of patches that must be applied when building 'component'
    with target 'version'.
    """
    component_version = Version(version_string)
    component_dir = SNAPCRAFT_PROJECT_DIR / "build-scripts" / "components" / component
    patches = []

    patch_directories = ["patches"]
    if strict:
        patch_directories += ["strict-patches"]

    for patch_dir_name in patch_directories:
        patches_dir = component_dir / patch_dir_name
        if not patches_dir.is_dir():
            continue

        candidates = [
            Version(path.name)
            for path in sorted(
                patches_dir.iterdir(), reverse=True
            )  # sort by reverse to handle exact matches
            if path.is_dir()
        ]
        patch_version = find_suitable_patch_version(candidates, component_version)
        if patch_version is not None:
            patches.extend(
                [p.resolve().as_posix() for p in (patches_dir / patch_version).iterdir()]
            )

    return patches


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("component", type=str)
    parser.add_argument("version", type=str)

    args = parser.parse_args()

    print("\n".join(get_patches_for(args.component, args.version, STRICT)))


if __name__ == "__main__":
    main()
