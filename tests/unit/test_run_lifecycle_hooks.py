import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run-lifecycle-hooks.py"


def _run(hook, snap_common):
    env = dict(os.environ, SNAP_COMMON=str(snap_common))
    return subprocess.run(
        [sys.executable, str(SCRIPT), hook],
        env=env,
        capture_output=True,
        text=True,
    )


def test_missing_hook_dir_is_noop(tmp_path):
    # hooks/<hook>.d does not exist: the runner must exit cleanly without a traceback.
    result = _run("reconcile-node", tmp_path)
    assert result.returncode == 0
    assert "Traceback" not in result.stderr


def test_runs_executable_hooks(tmp_path):
    hooks_dir = tmp_path / "hooks" / "reconcile-node.d"
    hooks_dir.mkdir(parents=True)
    sentinel = tmp_path / "ran"
    hook = hooks_dir / "10-touch"
    hook.write_text("#!/bin/bash\ntouch {}\n".format(sentinel))
    hook.chmod(0o755)

    result = _run("reconcile-node", tmp_path)
    assert result.returncode == 0
    assert sentinel.exists()


def test_skips_non_executable_hooks(tmp_path):
    hooks_dir = tmp_path / "hooks" / "reconcile-node.d"
    hooks_dir.mkdir(parents=True)
    sentinel = tmp_path / "ran"
    hook = hooks_dir / "10-touch"
    hook.write_text("#!/bin/bash\ntouch {}\n".format(sentinel))
    hook.chmod(0o644)

    result = _run("reconcile-node", tmp_path)
    assert result.returncode == 0
    assert not sentinel.exists()
