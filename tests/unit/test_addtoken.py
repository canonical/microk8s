from unittest import mock
from add_token import print_short


def test_single(capsys):
    with mock.patch(
        "add_token.get_network_info", return_value=["10.23.53.54", ["10.23.53.54"], "32"]
    ):
        print_short("t", "c")
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert output == "microk8s join 10.23.53.54:32/t/c"


def test_multiple(capsys):
    with mock.patch(
        "add_token.get_network_info", return_value=["d_ip", ["ip1", "ip2", "d_ip"], "4"]
    ):
        print_short("t", "c")
        captured = capsys.readouterr()
        all_outputs = captured.out.strip().split("\n")
        assert all_outputs == [
            "microk8s join d_ip:4/t/c",
            "microk8s join ip1:4/t/c",
            "microk8s join ip2:4/t/c",
        ]
