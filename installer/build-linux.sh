#!/bin/bash


virtualenv -p python3 .venv
source ./.venv/bin/activate
pip install -r requirements.txt
pyinstaller ./microk8s.spec
deactivate
rm -rf .venv
