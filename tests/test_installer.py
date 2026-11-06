# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import runpy
import subprocess

INSTALLER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'installer.py')


def run_installer(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, 'check_call', lambda cmd, **kwargs: calls.append((cmd, kwargs)))
    try:
        runpy.run_path(INSTALLER_PATH)
    except SystemExit as e:
        assert e.code == 0
    assert len(calls) == 1
    return calls[0]


def test_install_allows_externally_managed_python(monkeypatch):
    monkeypatch.delenv('ALL_PROXY', raising=False)
    cmd, kwargs = run_installer(monkeypatch)
    assert kwargs['env']['PIP_BREAK_SYSTEM_PACKAGES'] == '1'
    # pip < 23.0.1 rejects unknown flags, so the override must not be passed as a flag
    assert '--break-system-packages' not in cmd
    assert '--user' in cmd


def test_http_proxy_install_keeps_proxy_env(monkeypatch):
    monkeypatch.setenv('ALL_PROXY', 'http://proxy:8080')
    cmd, kwargs = run_installer(monkeypatch)
    assert kwargs['env']['ALL_PROXY'] == 'http://proxy:8080'
    assert kwargs['env']['PIP_BREAK_SYSTEM_PACKAGES'] == '1'


def test_https_proxy_install_keeps_proxy_env(monkeypatch, tmp_path):
    root_ca = tmp_path / 'root.ca.pem'
    root_ca.write_text('test root CA')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ALL_PROXY', 'https://proxy:8443')
    monkeypatch.setenv('GG_ROOT_CA_PATH', str(root_ca))
    cmd, kwargs = run_installer(monkeypatch)
    assert '--cert' in cmd
    assert kwargs['env']['ALL_PROXY'] == 'https://proxy:8443'
    assert kwargs['env']['PIP_BREAK_SYSTEM_PACKAGES'] == '1'
