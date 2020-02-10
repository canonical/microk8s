#!/bin/bash


virtualenv -p python3 .venv
source ./bin/activate
pip install -r requirements.txt
pyinstaller ./microk8s.spec
deactivate
rm -rf .venv
