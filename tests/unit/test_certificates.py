import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
UTILS_SH = REPO_ROOT / "microk8s-resources" / "actions" / "common" / "utils.sh"

# The component certificates used to be signed without any X.509 extension. openssl encodes
# such a certificate as v1, and rustls-based clients refuse to parse it, which is what broke
# `microk8s config` for them. See https://github.com/canonical/microk8s/issues/5447
V1_CERTIFICATE = """-----BEGIN CERTIFICATE-----
MIICuzCCAaMCCAECAwQFBgcIMA0GCSqGSIb3DQEBCwUAMBcxFTATBgNVBAMMDDEw
LjE1Mi4xODMuMTAeFw0yNDAxMDEwMDAwMDBaFw0zMzEyMjkwMDAwMDBaMCkxDjAM
BgNVBAMMBWFkbWluMRcwFQYDVQQKDA5zeXN0ZW06bWFzdGVyczCCASIwDQYJKoZI
hvcNAQEBBQADggEPADCCAQoCggEBALb5VewzRIdR1fE2A8JaCAI6utSJw7C2Bfjo
Bxm++PXxleK9gTONZ50JRIVLKZWBeONG20aB2WYaYj9pVC+9CnITkqMSZp6WUEXX
Tp+mHAPHiRvEPEQ5H3/kyaLAxLtTbrD56rmFomTT4G7sb43n1xsh+pX5wMv6L6oF
tvutLuMroxVeMgLsr12M4MnyiHx2RdSa1VuPWcq5n3FUzbFrVMVRhyVJTTE79oAn
X5cje62mPtX5ovD2Q3oH+tib3ESPdKDTqQbcCg3e6/lNzfxCbLn2fVzvELnTjDGr
qAY/YKskJDhGz/JypbgXuhjVQMFGDtSr8DT7UNuWlHZvaaTlL68CAwEAATANBgkq
hkiG9w0BAQsFAAOCAQEATcGm0XWXWq686CgoOoHeYH1XoCqSphX9HAXwA0ZWBvlv
JilVGKARSXhTrVk7VKLNWviW/uevM8347V3YnXciXvd96d05eR6JOHbhsywAaH0s
usS5rfhNT23CuKcCn6xZScUPWGyG0hoMhBIhFTPeRNj7zqkG/U9i2C0U3KJDHP8v
rdmfzgOCAqSqy4fCM5Nr4vkDARQw5fCb7tf+//oMk1p0tMG95/GU1yXyHHjHiTfj
8LGPNuKEHjujkV/gxryks60vxoxUhAVt1l8xoYL99jvNZ5/b4f+vL9dgTLcrKkTf
/jRFaTW3qfpIwjzS5FZbToYZAaI/q3kbKvNM35bpPA==
-----END CERTIFICATE-----
"""

# The certificates that create_user_certificates() signs with the cluster CA
CLIENT_CERTS = ["kubelet", "client", "proxy", "scheduler", "controller", "apiserver-kubelet-client"]

# Binaries that the functions under test reach through $SNAP
SNAP_BINARIES = {"bin": ["cat", "grep", "sed", "chmod", "chown"], "usr/bin": ["tail"]}


class Microk8s:
    """A $SNAP / $SNAP_DATA tree that is just complete enough to run the certificate helpers."""

    def __init__(self, root: Path):
        self.snap = root / "snap"
        self.snap_data = root / "data"
        self.certs = self.snap_data / "certs"

        self.certs.mkdir(parents=True)
        (self.snap_data / "var" / "lock").mkdir(parents=True)
        (self.snap / "actions" / "common").mkdir(parents=True)

        shutil.copy(UTILS_SH, self.snap / "actions" / "common" / "utils.sh")

        openssl = shutil.which("openssl")
        wrapper = self.snap / "openssl.wrapper"
        wrapper.write_text('#!/bin/sh\nexec {} "$@"\n'.format(openssl))
        wrapper.chmod(0o755)

        for directory, binaries in SNAP_BINARIES.items():
            (self.snap / directory).mkdir(parents=True, exist_ok=True)
            for binary in binaries:
                (self.snap / directory / binary).symlink_to(shutil.which(binary))

        self.openssl("genrsa", "-out", str(self.certs / "ca.key"), "2048")
        self.openssl(
            *"req -x509 -new -sha256 -nodes -days 3650".split(),
            *("-key", str(self.certs / "ca.key")),
            *("-subj", "/CN=10.152.183.1"),
            *("-addext", "basicConstraints=critical,CA:TRUE"),
            *("-addext", "keyUsage=critical,keyCertSign,cRLSign"),
            *("-out", str(self.certs / "ca.crt")),
        )

        self.component_key = self.certs / "component.key"
        self.openssl("genrsa", "-out", str(self.component_key), "2048")

    def openssl(self, *args) -> str:
        return subprocess.run(["openssl", *args], check=True, capture_output=True, text=True).stdout

    def run(self, script: str, stdin: str = None) -> subprocess.CompletedProcess:
        """Source utils.sh and run a snippet against it."""
        return subprocess.run(
            ["bash", "-c", 'source "$SNAP/actions/common/utils.sh"\n' + script],
            env={"SNAP": str(self.snap), "SNAP_DATA": str(self.snap_data), "PATH": "/usr/bin:/bin"},
            input=stdin,
            capture_output=True,
            text=True,
        )

    def sign(self, csr: str) -> str:
        result = self.run("sign_certificate", stdin=csr)
        assert result.returncode == 0, result.stderr
        return result.stdout

    def csr(self, subject: str, sans: str = None) -> str:
        args = ["req", "-new", "-sha256", "-subj", subject, "-key", str(self.component_key)]
        if sans:
            args += ["-addext", "subjectAltName = {}".format(sans)]
        return self.openssl(*args)

    def text(self, certificate: str) -> str:
        path = self.snap_data / "inspect.crt"
        path.write_text(certificate)
        return self.openssl("x509", "-in", str(path), "-noout", "-text")

    def write_cert(self, name: str, certificate: str) -> None:
        (self.certs / "{}.crt".format(name)).write_text(certificate)


@pytest.fixture
def microk8s(tmp_path):
    return Microk8s(tmp_path)


class TestSignCertificate:
    """sign_certificate() must always issue X.509 v3 certificates."""

    def test_certificate_without_sans_is_v3(self, microk8s):
        certificate = microk8s.sign(microk8s.csr("/CN=admin/O=system:masters"))

        assert "Version: 3 (0x2)" in microk8s.text(certificate)

    def test_certificate_carries_the_expected_extensions(self, microk8s):
        text = microk8s.text(microk8s.sign(microk8s.csr("/CN=system:kube-proxy")))

        assert "CA:FALSE" in text
        assert "Digital Signature, Key Encipherment" in text
        assert "TLS Web Server Authentication, TLS Web Client Authentication" in text
        assert "X509v3 Subject Key Identifier" in text
        assert "X509v3 Authority Key Identifier" in text

    def test_subject_alternative_names_are_preserved(self, microk8s):
        csr = microk8s.csr("/CN=system:node:node-1/O=system:nodes", sans="DNS:node-1, IP:10.0.0.1")

        text = microk8s.text(microk8s.sign(csr))

        assert "Version: 3 (0x2)" in text
        assert "DNS:node-1" in text
        assert "IP Address:10.0.0.1" in text


class TestCertificateIsX509V3:
    def test_detects_a_v3_certificate(self, microk8s):
        microk8s.write_cert("client", microk8s.sign(microk8s.csr("/CN=admin/O=system:masters")))

        assert microk8s.run('certificate_is_x509_v3 "$SNAP_DATA/certs/client.crt"').returncode == 0

    def test_detects_a_v1_certificate(self, microk8s):
        microk8s.write_cert("client", V1_CERTIFICATE)

        assert microk8s.run('certificate_is_x509_v3 "$SNAP_DATA/certs/client.crt"').returncode == 1

    def test_reports_a_missing_certificate(self, microk8s):
        assert microk8s.run('certificate_is_x509_v3 "$SNAP_DATA/certs/nothing.crt"').returncode == 1


class TestEnsureClientCertsV3:
    """Existing installations carry v1 certificates that have to be reissued on refresh."""

    REISSUE_STUB = 'create_user_certs_and_configs() { touch "$SNAP_DATA/reissued"; }\n'

    def populate(self, microk8s, v1_certs=()):
        v3 = microk8s.sign(microk8s.csr("/CN=admin/O=system:masters"))
        for name in CLIENT_CERTS:
            microk8s.write_cert(name, V1_CERTIFICATE if name in v1_certs else v3)

    def ensure(self, microk8s):
        result = microk8s.run(self.REISSUE_STUB + "ensure_client_certs_v3")
        assert result.returncode == 0, result.stderr
        return result.stdout.strip(), (microk8s.snap_data / "reissued").exists()

    def test_reissues_when_a_certificate_is_v1(self, microk8s):
        self.populate(microk8s, v1_certs=["client"])

        assert self.ensure(microk8s) == ("1", True)

    def test_reissues_when_a_certificate_is_missing(self, microk8s):
        self.populate(microk8s)
        (microk8s.certs / "proxy.crt").unlink()

        assert self.ensure(microk8s) == ("1", True)

    def test_does_nothing_when_every_certificate_is_v3(self, microk8s):
        self.populate(microk8s)

        assert self.ensure(microk8s) == ("0", False)

    def test_leaves_worker_nodes_alone(self, microk8s):
        self.populate(microk8s, v1_certs=CLIENT_CERTS)
        (microk8s.snap_data / "var" / "lock" / "clustered.lock").touch()

        assert self.ensure(microk8s) == ("0", False)
