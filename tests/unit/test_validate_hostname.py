import os
import shutil
import subprocess
from pathlib import Path

import pytest

UTILS_SH = Path(__file__).resolve().parents[2] / "microk8s-resources" / "actions" / "common" / "utils.sh"

# The kubelet certificate CN is "system:node:<hostname>" and X.509 limits CN to 64 characters,
# so the longest hostname we can accept is 64 - len("system:node:") = 52.
MAX_HOSTNAME_LENGTH = 64 - len("system:node:")

# Resolve the full path: on Windows, a bare "bash" may resolve to WSL's System32 launcher.
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is required")


@pytest.fixture
def snap(tmp_path):
    """Create a fake $SNAP whose bin/hostname prints $FAKE_HOSTNAME."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    hostname = bin_dir / "hostname"
    hostname.write_text('#!/usr/bin/env bash\necho "${FAKE_HOSTNAME}"\n')
    hostname.chmod(0o755)
    return tmp_path


def run_utils(snap, hostname, script):
    env = dict(
        os.environ,
        SNAP=snap.as_posix(),
        SNAP_DATA=snap.as_posix(),
        FAKE_HOSTNAME=hostname,
        UTILS_SH=UTILS_SH.as_posix(),
    )
    return subprocess.run(
        [BASH, "-c", f'source "$UTILS_SH"\n{script}'],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "hostname",
    [
        "node-1",
        "a" * (MAX_HOSTNAME_LENGTH - 1),
        "a" * MAX_HOSTNAME_LENGTH,
    ],
)
def test_validate_hostname_accepts_valid_length(snap, hostname):
    result = run_utils(snap, hostname, "validate_hostname")

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


@pytest.mark.parametrize(
    "hostname",
    [
        "a" * (MAX_HOSTNAME_LENGTH + 1),
        "a" * 63,
        "ip-10-0-0-1.very-long-subdomain.us-west-2.compute.internal",
    ],
)
def test_validate_hostname_rejects_too_long(snap, hostname):
    result = run_utils(snap, hostname, "validate_hostname")

    assert result.returncode != 0
    assert "too long" in result.stderr
    assert hostname in result.stderr
    assert f"at most {MAX_HOSTNAME_LENGTH} characters" in result.stderr


def test_validate_hostname_does_not_leak_variables(snap):
    result = run_utils(
        snap,
        "node-1",
        'hostname=outer; cn=outer; validate_hostname; echo "$hostname $cn"',
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "outer outer"


def test_validate_hostname_does_not_create_stray_files(snap, tmp_path, monkeypatch):
    # A buggy `[ x > 64 ]` comparison redirects output to a file named "64".
    monkeypatch.chdir(tmp_path)
    run_utils(snap, "a" * (MAX_HOSTNAME_LENGTH + 1), "validate_hostname")

    assert not (tmp_path / "64").exists()


STUB_CERT_FUNCTIONS = """
create_user_certificates() { echo "certificates-created"; }
create_user_kubeconfigs() { echo "kubeconfigs-created"; }
"""


def test_create_user_certs_and_configs_runs_for_valid_hostname(snap):
    result = run_utils(snap, "node-1", STUB_CERT_FUNCTIONS + "create_user_certs_and_configs")

    assert result.returncode == 0, result.stderr
    assert "certificates-created" in result.stdout
    assert "kubeconfigs-created" in result.stdout


def test_create_user_certs_and_configs_aborts_for_long_hostname(snap):
    result = run_utils(
        snap,
        "a" * (MAX_HOSTNAME_LENGTH + 1),
        STUB_CERT_FUNCTIONS + "create_user_certs_and_configs",
    )

    assert result.returncode != 0
    assert "too long" in result.stderr
    assert "certificates-created" not in result.stdout
    assert "kubeconfigs-created" not in result.stdout
