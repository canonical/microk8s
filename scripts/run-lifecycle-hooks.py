#!/usr/bin/env python3

from pathlib import Path
import os
import click
import subprocess

SNAP_COMMON = Path(os.getenv("SNAP_COMMON"))
TIMEOUT = 120


@click.command("run-lifecycle-hooks")
@click.argument("hook")
def main(hook: str):
    hooks_dir = SNAP_COMMON / "hooks" / f"{hook}.d"
    hooks = os.listdir(hooks_dir)
    for hook in sorted(hooks):
        try:
            if not (os.stat(hooks_dir / hook).st_mode & 0o100):
                # ignore non-executable files
                continue

            subprocess.run([hooks_dir / hook], timeout=TIMEOUT)
        except (subprocess.CalledProcessError, OSError):
            pass


if __name__ == "__main__":
    main()
