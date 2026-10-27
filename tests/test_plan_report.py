"""Synthetic sentinel privacy tests for the public report boundary."""
import argparse
import copy
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from test_description_repair import ITEM

import geni_upload as g
import plan_report as r
import source_details as s

MANIFEST = {'targets': [{'profile_id': '991234567890', 'expect_name': 'ZZPrivate ZZName',
    'documents': [{'title': 'ZZPrivateTitle', 'source_url': 'https://example.invalid/ZZPrivateURL',
                   'description_en': 'ZZPrivateDescription', 'file': 'ZZPrivatePath',
                   'also_tag': ['992345678901']}],
    'photos': [{'title': 'ZZPrivatePhoto', 'date': '1777-06-09',
                'description_en': 'ZZPrivatePhotoDescription', 'file': 'ZZPrivateFile'}]},
    {'profile_id': '992345678901', 'expect_name': 'ZZOther ZZName'}]}


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from strings(value)


def assert_private_absent(text, manifest):
    for value in strings(manifest):
        assert value not in text


def test_counts_and_renderer_never_include_any_manifest_value():
    data = r.report('plan')
    data['counts'] = r.upload_counts(MANIFEST)
    assert data['counts'] == {'sources': 2, 'profiles': 2, 'tags': 3, 'descriptions': 2}
    assert_private_absent(r.render(data), MANIFEST)
    item = copy.deepcopy(ITEM)
    item['manual_facts'] = ['ZZPrivateManualFact']
    data = r.report('details-plan')
    data['counts'] = r.details_counts([item])
    assert data['counts'] == {'sources': 1, 'profiles': 1, 'tags': 0, 'descriptions': 1}
    assert_private_absent(r.render(data), item)


@pytest.mark.parametrize('failure', ['no_token', 'identity', 'listing', 'schema', 'throttle'])
def test_upload_failures_are_not_ready_and_do_not_publish_error_text(tmp_path, failure):
    destination = tmp_path / 'report'
    args = argparse.Namespace(manifest='ZZPrivateManifestPath', token_file=None)
    def verify(*args):
        if failure == 'identity':
            raise g.ApiError('ZZPrivateException')
        if failure == 'throttle':
            raise g.ThrottledError('ZZPrivateException')
        return ('991234567890', 'ZZPrivateServedName')
    with patch.dict(os.environ, {'GENI_PLAN_REPORT': str(destination)}), \
            patch.object(g, 'load_manifest', return_value=copy.deepcopy(MANIFEST)) as load, \
            patch.object(g, 'get_token', return_value=None if failure == 'no_token' else 'ZZtoken'), \
            patch.object(g, 'verify_profile', verify), \
            patch.object(g, 'list_tagged', return_value=None if failure == 'listing' else []):
        if failure == 'schema':
            load.side_effect = g.ApiError('ZZPrivateSchemaText')
        try:
            g.cmd_plan(args)
        except g.ApiError:
            pass
    data = json.loads(destination.read_text())
    text = r.render(data)
    assert 'Safe to run: no' in text
    assert 'ZZPrivate' not in text
    assert_private_absent(text, MANIFEST)


def test_upload_success(tmp_path):
    destination = tmp_path / 'report'
    with patch.dict(os.environ, {'GENI_PLAN_REPORT': str(destination)}), \
            patch.object(g, 'load_manifest', return_value=copy.deepcopy(MANIFEST)), \
            patch.object(g, 'get_token', return_value='ZZtoken'), \
            patch.object(g, 'verify_profile', return_value=('99', 'ZZPrivateServedName')), \
            patch.object(g, 'list_tagged', return_value=[]):
        assert g.cmd_plan(argparse.Namespace(manifest='ZZpath')) == 0
    text = r.render(json.loads(destination.read_text()))
    assert 'Safe to run: yes' in text
    assert 'ZZPrivate' not in text


@pytest.mark.parametrize('failure', ['schema', 'token', 'no_token', 'check', None])
def test_details_paths_never_publish_manifest_or_exception(tmp_path, failure):
    destination = tmp_path / 'report'
    argv = ['source_details', 'plan', '--manifest', 'ZZPrivatePath']
    with patch.dict(os.environ, {'GENI_PLAN_REPORT': str(destination)}), \
            patch.object(sys, 'argv', argv), \
            patch.object(s, 'load_records', return_value=[copy.deepcopy(ITEM)]) as load, \
            patch.object(s.api, 'get_token', return_value='ZZtoken') as token, \
            patch.object(s, 'checked_plan', return_value=[]) as check:
        if failure == 'schema':
            load.side_effect = s.api.ApiError('ZZPrivateSchema')
        if failure == 'token':
            token.side_effect = OSError('ZZPrivateTokenPath')
        if failure == 'no_token':
            token.return_value = None
        if failure == 'check':
            check.side_effect = s.api.ApiError('ZZPrivateObjectID')
        assert s.main() == (0 if failure is None else 1)
    text = r.render(json.loads(destination.read_text()))
    assert 'ZZPrivate' not in text
    assert ('Safe to run: yes' in text) == (failure is None)
    assert_private_absent(text, ITEM)


@pytest.mark.parametrize('bad', [None, [], {'private': 'ZZPrivate'},
    {**r.report('plan'), 'mode': 'ZZPrivate'},
    {**r.report('plan'), 'complete': 'ZZPrivate'},
    {**r.report('plan'), 'counts': dict.fromkeys(r.COUNTS, 'ZZPrivate')},
    {**r.report('plan'), 'checks': dict.fromkeys(r.CHECKS, 'ZZPrivate')},
    {**r.report('plan'), 'counts': dict.fromkeys(r.COUNTS, True)},
    {**r.report('plan'), 'counts': dict.fromkeys(r.COUNTS, -1)}])
def test_public_boundary_rejects_injected_report_and_only_writes_fixed_fallback(tmp_path, bad):
    src, dst = tmp_path / 'input', tmp_path / 'summary'
    src.write_text(json.dumps(bad))
    with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(dst)}), \
            patch.object(sys, 'argv', ['plan_report', str(src)]):
        r.main()
    assert 'ZZPrivate' not in dst.read_text()
    assert 'Safe to run: no' in dst.read_text()


def test_incomplete_cannot_claim_ready():
    data = r.report('plan')
    data['checks'] = dict.fromkeys(r.CHECKS, 'pass')
    assert 'Safe to run: no' in r.render(data)


def test_workflow_uses_only_pinned_value_free_renderer():
    workflow = (Path(__file__).parents[1] / '.github/workflows/geni-upload.yml').read_text()
    assert '-e GENI_PLAN_REPORT=/run/plan-report/report.json' in workflow
    assert '"$IMAGE" /opt/plan_report.py /run/plan-report/report.json' in workflow
    assert '--network none --entrypoint python' in workflow
    assert 'cat "$RAW" >> "$GITHUB_STEP_SUMMARY"' not in workflow
    assert 'COPY plan_report.py /opt/plan_report.py' in (
        Path(__file__).parents[1] / 'Dockerfile').read_text()


def test_old_image_cannot_attempt_missing_renderer_or_claim_ready():
    workflow = (Path(__file__).parents[1] / '.github/workflows/geni-upload.yml').read_text()
    assert 'PLAN_SUMMARY_IMAGE_READY: "no"' in workflow
    assert '[ "${PLAN_SUMMARY_IMAGE_READY:-no}" = "yes" ]; then' in workflow
    assert '[ "${PLAN_SUMMARY_IMAGE_READY:-no}" != "yes" ]; then' in workflow
    assert 'Summary image not released; inspect the protected log.' in workflow


def test_malformed_json_has_fixed_fallback(tmp_path):
    src, dst = tmp_path / 'input', tmp_path / 'summary'
    src.write_text('{"ZZPrivateMalformed":')
    with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(dst)}), \
            patch.object(sys, 'argv', ['plan_report', str(src)]):
        r.main()
    assert 'ZZPrivate' not in dst.read_text()
    assert 'Safe to run: no' in dst.read_text()
