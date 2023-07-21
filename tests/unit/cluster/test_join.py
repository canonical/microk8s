import os
from shutil import rmtree
from unittest import mock

import join
from click.testing import CliRunner
from join import join as command


def test_command_help_arguments():
    runner = CliRunner()
    for help_arg in ("-h", "--help"):
        result = runner.invoke(command, [help_arg])
        assert result.exit_code == 0
        assert "Join the node to a cluster" in result.output


def test_command_errors_if_no_arguments():
    runner = CliRunner()
    result = runner.invoke(command, [])
    assert result.exit_code != 0
    assert "Error: Missing argument" in result.output


@mock.patch("subprocess.check_call")
@mock.patch("os.chown")
@mock.patch("os.chmod")
@mock.patch("subprocess.check_output")
@mock.patch("time.sleep")
def test_join_dqlite_master_node(
    mock_sleep,
    mock_subprocess_check_output,
    mock_chmod,
    mock_chown,
    mock_subprocess_check_call,
    tmp_path,
):
    """
    Test the join operation. Create a directory layout and let the join operation work with it.
    """
    snapcommon = tmp_path / "snapcommon"
    snapdata = tmp_path / "snapdata" / "rev-123"
    snapdatacurrnet = tmp_path / "snapdata" / "current"
    snap = tmp_path / "snap"
    args = snapdata / "args"
    certs = snapdata / "certs"
    credentials = snapdata / "credentials"
    dqlite = snapdata / "var" / "kubernetes" / "backend"

    join.snapdata_path = snapdata
    join.snap_path = snap
    join.cluster_dir = f"{snapdata}/var/kubernetes/backend"
    join.cluster_backup_dir = f"{snapdata}/var/kubernetes/backend.backup"
    join.cluster_cert_file = f"{join.cluster_dir}/cluster.crt"
    join.cluster_key_file = f"{join.cluster_dir}/cluster.key"

    os.environ["SNAP"] = str(snap)
    os.environ["SNAP_DATA"] = str(snapdata)
    os.environ["SNAP_COMMON"] = str(snapcommon)

    def create_dir_layout(tokens):
        for d in [
            snapcommon,
            snapdata,
            dqlite,
            snap / "meta",
            args / "cni-network",
            snapdata / "var" / "lock",
            certs,
            credentials,
        ]:
            if os.path.exists(d):
                rmtree(d, ignore_errors=True)
            os.makedirs(d, exist_ok=True)

        if os.path.exists(snapdatacurrnet):
            os.remove(snapdatacurrnet)
        snapdatacurrnet
        os.symlink(snapdata, snapdatacurrnet)
        for cert in ["ca", "client", "controller", "proxy", "scheduler", "kubelet"]:
            with open(certs / f"{cert}.crt", "w") as ca:
                ca.write(f"{cert}_data")
            with open(certs / f"{cert}.key", "w") as ca:
                ca.write(f"{cert}_key_data")

        with open(snap / "meta" / "snap.yaml", "w") as f:
            f.write("confinement: classic")
        with open(certs / "serviceaccount.key", "w") as f:
            f.write("service_account_key_data")
        with open(args / "kube-apiserver", "w") as f:
            f.write("--some-argument")
        with open(dqlite / "info.yaml", "w") as f:
            f.write("Address: 127.0.0.1:19001\nID: 3297041220608546238\nRole: 0\n")
        with open(args / "cni-network" / "cni.yaml", "w") as f:
            f.write("can-reach\n")
        with open(snap / "client.config.template", "w") as f:
            f.write("token\nUSERNAME")
        with open(snap / "client-x509.config.template", "w") as f:
            f.write("x509\nUSERNAME")
        for config in [
            "client.config",
            "controller.config",
            "proxy.config",
            "scheduler.config",
            "kubelet.config",
        ]:
            with open(credentials / config, "w") as f:
                f.write("kubeconfig")

    create_dir_layout(tokens=False)

    info = {
        "hostname_override": "no-host",
        "ca": "new_ca_bytes",
        "ca_key": "new_ca_key_bytes",
        "service_account_key": "srv_account_key_bytes",
        "kubelet_args": "--some-kubelet-arg",
        "callback_token": "123callback456",
        "cluster_cert": "dqlite_cert",
        "cluster_key": "dqlite_cert_key",
        "voters": "none",
    }

    join.join_dqlite_master_node(info, "123.123.123.123")

    # Assert we stored the CA and the dqlite certs
    mock_chmod.assert_any_call(str(certs / "ca.crt"), 0o660)
    mock_chmod.assert_any_call(str(certs / "ca.key"), 0o660)
    mock_chmod.assert_any_call(str(dqlite / "cluster.crt"), 0o660)
    mock_chmod.assert_any_call(str(dqlite / "cluster.key"), 0o660)

    # Assert we restart services
    mock_subprocess_check_call.assert_any_call("snapctl stop microk8s.daemon-kubelite".split())
    mock_subprocess_check_call.assert_any_call("snapctl start microk8s.daemon-kubelite".split())
    mock_subprocess_check_call.assert_any_call("snapctl stop microk8s.daemon-k8s-dqlite".split())
    mock_subprocess_check_call.assert_any_call("snapctl start microk8s.daemon-k8s-dqlite".split())

    # Assert we created admin kubeconfig from certificate
    mock_subprocess_check_call.assert_any_call(
        [f"{snap}/actions/common/utils.sh", "create_user_certs_and_configs"], stdout=-3, stderr=-3
    )

    mock_subprocess_check_call.reset_mock()

    # Check joining with tokens based
    create_dir_layout(tokens=True)
    mock_subprocess_check_call.reset_mock()
    info["admin_token"] = "some-token"
    join.join_dqlite_master_node(info, "123.123.123.123")

    mock_subprocess_check_call.assert_any_call(
        [f"{snap}/actions/common/utils.sh", "create_user_certs_and_configs"], stdout=-3, stderr=-3
    )
