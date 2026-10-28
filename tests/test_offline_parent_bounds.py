import hashlib
import http.client
import json
import os
import socket
import subprocess
import urllib.request

import pytest

import parent_envelope
import parent_plan
from people_core import Blocked, digest
from tests.test_parent_envelope import fixture


@pytest.mark.parametrize('bad', [object(), {1: 'ZZprivate'}, {'ZZ': object()}])
def test_unsupported_hash_is_fixed_blocked(bad):
    with pytest.raises(Blocked) as error: digest(bad)
    assert 'ZZ' not in str(error.value)


def test_depth_and_cycle_blocked_before_serializer():
    value = {}
    value['cycle'] = value
    with pytest.raises(Blocked): digest(value)
    value = []
    for _ in range(34): value = [value]
    with pytest.raises(Blocked): digest(value)


def test_valid_hash_bytes_unchanged():
    value = {'ZZ': ['שם', True, False, None, 2, 1.5]}
    expected = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                         ensure_ascii=False).encode()).hexdigest()
    assert digest(value) == expected


def test_proposal_render_envelope_never_network_or_subprocess(monkeypatch):
    def deny(*a, **k): pytest.fail('offline operation attempted process or network')
    for target, name in [(socket, 'socket'), (subprocess, 'run'), (subprocess, 'Popen'),
                         (urllib.request, 'urlopen'), (urllib.request.OpenerDirector, 'open'),
                         (http.client.HTTPConnection, 'request')]:
        monkeypatch.setattr(target, name, deny)
    for name in dir(os):
        if name in ('system', 'popen', 'startfile') or name.startswith(
                ('exec', 'spawn', 'fork', 'posix_spawn')):
            monkeypatch.setattr(os, name, deny)
    plan, value = fixture()  # also constructs and validates a proposal
    assert '<html' in parent_plan.render(plan)
    envelope = parent_envelope.draft(plan, value)
    assert parent_envelope.review(envelope, plan, value, 1100)['creation_enabled'] is False


def test_cli_nested_json_fixed_failure(tmp_path, capsys):
    manifest, pins = tmp_path/'manifest', tmp_path/'pins'
    manifest.write_text('[' * 1500 + '0' + ']' * 1500)
    pins.write_text('{}')
    for path in (manifest, pins): path.chmod(0o600)
    assert parent_plan.main(['--manifest-file', str(manifest), '--pins-file', str(pins),
                             '--output-dir', str(tmp_path/'out')]) == 1
    assert capsys.readouterr().out == 'parent-plan blocked; review protected inputs\n'
