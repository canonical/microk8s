from common.auxiliary import Auxiliary
from unittest.mock import Mock, patch


def get_mocked_args(disk=1, mem=1, cpu=1):
    args = Mock(mem=mem, disk=disk, cpu=cpu)
    return args


@patch("common.auxiliary.psutil.virtual_memory")
def test_has_enough_memory(virtual_memory_mock):
    args = get_mocked_args(mem=50)
    host = Auxiliary(args)

    # 3 Bytes of memory
    virtual_memory_mock.return_value.total = 3
    assert host.has_enough_memory() is False

    # 300 GB of memory
    virtual_memory_mock.return_value.total = 300 * 1024 * 1024 * 1024
    assert host.has_enough_memory() is True


@patch("common.auxiliary.psutil.cpu_count")
def test_has_enough_cpus(cpu_count_mock):
    args = get_mocked_args(cpu=4)
    host = Auxiliary(args)

    cpu_count_mock.return_value = 3
    assert host.has_enough_cpus() is False

    cpu_count_mock.return_value = 5
    assert host.has_enough_cpus() is True


@patch("common.auxiliary.disk_usage")
def test_has_enough_disk_space(disk_usage_mock):
    args = get_mocked_args(disk=10)
    host = Auxiliary(args)

    disk_usage_mock.return_value.free = 3
    assert host.has_enough_disk_space() is False

    disk_usage_mock.return_value.free = 50 * 1024 * 1024 * 1024
    assert host.has_enough_disk_space() is True
