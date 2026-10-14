#!/bin/bash

set -euo pipefail

python3 -m venv .venv

source ./.venv/bin/activate
pip install --upgrade "pip==23.3.1"
pip install -r requirements.txt

pyinstaller ./microk8s.spec

deactivate 2>/dev/null || true
rm -rf .venv

