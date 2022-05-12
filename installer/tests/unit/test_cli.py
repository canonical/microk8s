from cli.microk8s import install
from unittest.mock import patch, MagicMock
import pytest


@patch("common.auxiliary.Auxiliary.has_enough_cpus", return_value=False)
def test_install_exits_on_cpus_requested_exceed_available_on_host(has_enough_cpus_mock):
    with pytest.raises(SystemExit) as exc:
        install(MagicMock())
    assert exc.value.code == 1
    has_enough_cpus_mock.assert_called_once()


@patch("common.auxiliary.Auxiliary.has_enough_memory", return_value=False)
@patch("common.auxiliary.Auxiliary.has_enough_cpus", return_value=True)
def test_install_exits_on_memory_requested_exceed_available_on_host(
    has_enough_cpus_mock,
    has_enough_memory_mock,
):
    with pytest.raises(SystemExit) as exc:
        install(MagicMock())
    assert exc.value.code == 1
    has_enough_memory_mock.assert_called_once()
