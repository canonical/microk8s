# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016-2019 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import hashlib
import logging
import os
import shutil
import sys

if sys.version_info < (3, 6):
    pass


logger = logging.getLogger(__name__)


def _file_reader_iter(path: str, block_size=2 ** 20):
    with open(path, "rb") as f:
        block = f.read(block_size)
        while len(block) > 0:
            yield block
            block = f.read(block_size)


def calculate_sha3_384(path: str) -> str:
    """Calculate sha3 384 hash, reading the file in 1MB chunks."""
    return calculate_hash(path, algorithm="sha3_384")


def calculate_hash(path: str, *, algorithm: str) -> str:
    """Calculate the hash for path with algorithm."""
    # This will raise an AttributeError if algorithm is unsupported
    hasher = getattr(hashlib, algorithm)()

    for block in _file_reader_iter(path):
        hasher.update(block)
    return hasher.hexdigest()


def is_dumb_terminal():
    """Return True if on a dumb terminal."""
    is_stdout_tty = os.isatty(1)
    is_term_dumb = os.environ.get("TERM", "") == "dumb"
    return not is_stdout_tty or is_term_dumb


def get_kubectl_directory() -> str:
    """
    Get the correct directory to install kubectl into,
    we can then call this when running `microk8s kubectl`
    without interfering with any systemwide install.

    :return: String
    """
    if sys.platform == "win32":
        if getattr(sys, "frozen", None):
            d = os.path.dirname(sys.executable)
        else:
            d = os.path.dirname(os.path.abspath(__file__))

        return os.path.join(d, "kubectl")
    else:
        full_path = shutil.which("kubectl")
        return os.path.dirname(full_path)


def get_kubeconfig_path():
    """Return a MicroK8s specific kubeconfig path."""
    if sys.platform == "win32":
        return os.path.join(os.environ.get("LocalAppData"), "MicroK8s", "config")
    else:
        return os.path.join(os.path.expanduser("~"), ".microk8s", "config")


def clear_kubeconfig():
    """Clean kubeconfig file."""
    if os.path.isdir(get_kubeconfig_path()):
        shutil.rmtree(os.path.dirname(get_kubeconfig_path()))
