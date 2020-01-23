#!/bin/bash


python3 -m venv .
source ./bin/activate
pip install -r requirements.txt
pyinstaller ./microk8s.spec
deactivate
