from common.utils import parse_xable_addon_args

import pytest

ADDONS = [
    ("core", "addon1"),
    ("core", "addon2"),
    ("community", "addon3"),
    ("core", "conflict"),
    ("community", "conflict"),
]


@pytest.mark.parametrize(
    "args, result",
    [
        (["addon1"], [("core", "addon1", [])]),
        (["core/conflict"], [("core", "conflict", [])]),
        (["community/conflict"], [("community", "conflict", [])]),
        (["community/conflict", "--with-arg"], [("community", "conflict", ["--with-arg"])]),
        (["addon1", "--with-arg"], [("core", "addon1", ["--with-arg"])]),
        (
            ["addon1:arg1", "addon2:arg2", "addon3"],
            [
                ("core", "addon1", ["arg1"]),
                ("core", "addon2", ["arg2"]),
                ("community", "addon3", []),
            ],
        ),
        (
            ["addon1:arg1", "addon2:arg2", "community/conflict"],
            [
                ("core", "addon1", ["arg1"]),
                ("core", "addon2", ["arg2"]),
                ("community", "conflict", []),
            ],
        ),
        (
            ["core/addon1:arg1", "addon2:arg2", "community/conflict:arg3"],
            [
                ("core", "addon1", ["arg1"]),
                ("core", "addon2", ["arg2"]),
                ("community", "conflict", ["arg3"]),
            ],
        ),
    ],
)
def test_parse_addons_args(args, result):
    addons = parse_xable_addon_args(args, ADDONS)
    assert addons == result
