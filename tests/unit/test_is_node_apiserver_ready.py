import os
import subprocess
from pathlib import Path

UTILS = (
    Path(__file__).resolve().parents[2] / "microk8s-resources" / "actions" / "common" / "utils.sh"
)


def _call_with_fake_kubectl(tmp_path, kubectl_exit):
    snap = tmp_path / "snap"
    snap.mkdir()
    kubectl = snap / "kubectl"
    kubectl.write_text("#!/bin/bash\nexit {}\n".format(kubectl_exit))
    kubectl.chmod(0o755)

    snap_data = tmp_path / "data"
    (snap_data / "credentials").mkdir(parents=True)
    (snap_data / "credentials" / "kubelet.config").write_text("dummy")

    env = dict(os.environ, SNAP=str(snap), SNAP_DATA=str(snap_data))
    return subprocess.run(
        ["bash", str(UTILS), "is_node_apiserver_ready"],
        env=env,
        capture_output=True,
        text=True,
    )


def test_ready_when_kubectl_succeeds(tmp_path):
    assert _call_with_fake_kubectl(tmp_path, 0).returncode == 0


def test_not_ready_when_kubectl_fails(tmp_path):
    assert _call_with_fake_kubectl(tmp_path, 1).returncode == 1
