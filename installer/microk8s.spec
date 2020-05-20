# -*- mode: python ; coding: utf-8 -*-

import PyInstaller.config
PyInstaller.config.CONF['distpath'] = "./"

block_cipher = None

a = Analysis(
    ['microk8s.py'],
    pathex=[''],
    binaries=[],
    datas=[],
    hiddenimports=[
        "click",
        "responses",
        "pkg_resources.py2_warn"
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='microk8s',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    icon="windows/microk8s.ico",
    console=True
)

