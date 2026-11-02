"""Synthetic ZZ single-child experiment. No live credentials or endpoints."""
import base64
import json

import pytest

import geni_union_child_create as p
import geni_union_child_model as m
from tests.test_geni_protected_household import (
    ANCHOR,
    OWNER,
    TOKEN,
    UNION,
    ModelIO,
    env,
)
from tests.test_geni_protected_household import (
    plan as old_plan,
)
from tests.test_guarded_family_additions import Store


def plan():
    c = old_plan(); c['entries'] = c['entries'][:1]
    c['accept_omitted_union_fields'] = False
    return c


@pytest.fixture(autouse=True)
def clocks(monkeypatch):
    monkeypatch.setattr(p.time, 'time', lambda: 200)
    monkeypatch.setattr(p.time, 'sleep', lambda _: None)


def wired(c, anomaly=None, ack=None, evidence=None):
    v = p.ScopedVendor(TOKEN, c); model = ModelIO(c, anomaly); calls = []
    def request(method, route, body=None):
        v.admit_vendor(method, route); calls.append((method, route, body))
        if method == 'POST':
            actual = model.add(c['anchor'], c['mode'], body)
            return ack if ack is not None else actual
        node = route.split('/api/')[1].split('?')[0].split('/')[0]
        if '/immediate-family?' in route: return model.get_family(node)
        if '/union-' in route: return model.get_union(node)
        return model.get_profile(node)
    v.request = request
    return v, model, calls, p.IO(v, evidence=evidence)


def run(c=None, anomaly=None, ack=None, evidence=None, store=None):
    c = c or plan(); saved = []
    v, model, calls, io = wired(c, anomaly, ack, evidence or saved.append)
    result = m.execute(c, io, store or Store(), lambda x: b'ZZ-cipher', lambda: 200)
    return result, v, model, calls, saved


def test_one_union_target_post_then_all_proofs():
    r, v, model, calls, saved = run()
    assert r['phase'] == 'VERIFIED' and len(model.posts) == 1
    assert [route for method, route, _ in calls if method == 'POST'] == ['/api/' + UNION + '/add-child']
    assert len([x for x in calls if x[0] == 'GET']) == 12
    assert next(x for x in saved if x['stage'] == 'ack_raw')['value']['id'] == 'profile-99201'
    with pytest.raises(m.shared.Blocked): v.admit_vendor('POST', '/api/' + UNION + '/add-child')


@pytest.mark.parametrize('bad', ['partner', 'multiple', 'omitted'])
def test_policy_rejects_other_modes_multiple_and_omitted_proofs(bad):
    c = plan()
    if bad == 'partner': c['mode'] = 'partner'; c['target_union'] = None
    if bad == 'multiple': c['entries'] = old_plan()['entries']
    if bad == 'omitted': c['accept_omitted_union_fields'] = True
    with pytest.raises(m.shared.Blocked): p.ScopedVendor(TOKEN, c)


@pytest.mark.parametrize('ack', [{'id': UNION, 'children': ['profile-99201']}, {},
                               {'id': OWNER}, {'error': 'ZZ'}, {'id': 'ZZ-invalid'}])
def test_unknown_or_union_ack_saved_then_stop_no_discovery(ack):
    r, v, model, calls, saved = run(ack=ack)
    assert r['phase'] == 'STOPPED' and len(model.posts) == 1 and v.pending
    assert saved[-1]['stage'] == 'ack_raw' and saved[-1]['value'] == ack
    post = next(i for i, x in enumerate(calls) if x[0] == 'POST')
    assert len(calls) == post + 1


@pytest.mark.parametrize('anomaly', ['privacy', 'description', 'claimed', 'extra_edge',
                                   'wrong_union', 'lost_response', 'omitted'])
def test_anomalies_stop_never_second_post(anomaly):
    r, _v, model, calls, _ = run(anomaly=anomaly)
    assert r['phase'] == 'STOPPED'
    assert len(model.posts) == (0 if anomaly == 'omitted' else 1)
    assert sum(method == 'POST' for method, _, _ in calls) <= 1


def test_ack_storage_failure_closes_pending_before_profile_read():
    def save(r):
        if r['stage'] == 'ack_raw': raise OSError()
    r, v, model, calls, _ = run(evidence=save)
    assert r['phase'] == 'STOPPED' and v.pending and len(model.posts) == 1
    assert calls[-1][0] == 'POST'


def test_routes_never_profile_or_other_union_or_update():
    v = p.ScopedVendor(TOKEN, plan())
    for method, route in [('POST', '/api/' + ANCHOR + '/add-child'),
                          ('POST', '/api/union-99999/add-child'),
                          ('POST', '/api/' + UNION + '/update'),
                          ('DELETE', '/api/' + UNION),
                          ('GET', '/api/profile-99999?fields=' + p.FIELDS + '&only_ids=true')]:
        with pytest.raises(m.shared.Blocked): v.admit_vendor(method, route)


def test_marker_reuse_shared_with_old_workflow():
    c = plan(); st = Store(); run(c, store=st)
    c['expires_at'] += 50
    r, _, model, _, _ = run(c, store=st)
    assert r['phase'] == 'STOPPED' and not model.posts


def test_real_source_decode_hash_and_consistency_to_boundary(tmp_path, monkeypatch):
    c = plan(); e = {k.replace('HOUSEHOLD_CREATE_', 'UNION_CHILD_'): v
                     for k, v in env(c, tmp_path).items()}
    e['UNION_CHILD_CONFIRM'] = 'CREATE_ONE_UNION_CHILD'
    requests = []
    class Git:
        def request(self, method, route, body=None):
            requests.append((method, route))
            if '/contents/' not in route: return {'private': True, 'full_name': 'ZZ-owner/ZZ-source'}
            raw = json.dumps(c).encode()
            return {'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(raw).decode(), 'size': len(raw)}
    monkeypatch.setattr(p, 'HTTPS', lambda *_a, **_k: Git())
    monkeypatch.setattr(p, 'encrypt', lambda *_: b'ZZ-cipher')
    seen = []
    def boundary(token, actual): seen.append(actual); raise OSError()
    monkeypatch.setattr(p, 'ScopedVendor', boundary)
    assert not p.run(e) and seen == [c]
    assert all(method == 'GET' for method, _ in requests)


def test_workflow_separate_secret_same_human_protection():
    from pathlib import Path
    s = (Path(__file__).resolve().parents[1] / '.github/workflows/geni-union-child-create.yml').read_text()
    for text in ['environment: father-create', 'UNION_CHILD_PACKAGE_JSON',
                 'CREATE_ONE_UNION_CHILD', 'github.run_attempt == 1',
                 'github.sha == inputs.executor_sha', 'group: one-time-parent-pilot',
                 'cancel-in-progress: false', 'persist-credentials: false', 'if: always()']:
        assert text in s
    assert 'HOUSEHOLD_CREATE_PACKAGE_JSON' not in s


@pytest.mark.parametrize('status', [301, 302, 429, 500])
def test_real_https_post_no_redirect_or_retry(status, monkeypatch):
    import one_time_parent_pilot as transport
    sent = []
    class Response:
        def __init__(self): self.status = status
        def getheader(self, name): return 'https://evil.invalid/ZZ' if name == 'Location' else 'application/json'
        def read(self, _): return b'{"error":"ZZ-private"}'
    class Connection:
        def __init__(self, host, port, timeout):
            assert host == 'www.geni.com' and port == 443 and timeout == 20
        def request(self, method, route, **kwargs): sent.append((method, route))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(transport.http.client, 'HTTPSConnection', Connection)
    v = p.ScopedVendor(TOKEN, plan()); io = p.IO(v, evidence=lambda _: None)
    with pytest.raises(transport.TransportStop): io.add(ANCHOR, 'child', m.vendor_payload(plan()['entries'][0]['payload']))
    assert sent == [('POST', '/api/' + UNION + '/add-child')]
    assert v.pending and v.post_count == 1
    with pytest.raises(m.shared.Blocked): io.add(ANCHOR, 'child', m.vendor_payload(plan()['entries'][0]['payload']))
    assert len(sent) == 1


def test_omitted_union_children_after_create_is_not_success():
    c = plan(); v, model, calls, io = wired(c, evidence=lambda _: None)
    original = model.get_union
    def union(node):
        actual = original(node)
        if model.posts: actual.pop('children')
        return actual
    model.get_union = union
    result = m.execute(c, io, Store(), lambda _: b'ZZ-cipher', lambda: 200)
    assert result['phase'] == 'STOPPED' and len(model.posts) == 1 and v.pending
    assert calls[-1][0] == 'GET'


def test_no_evidence_sink_means_no_send():
    c = plan(); _v, model, calls, io = wired(c)
    result = m.execute(c, io, Store(), lambda _: b'ZZ-cipher', lambda: 200)
    assert result['phase'] == 'STOPPED' and not model.posts
    assert not any(x[0] == 'POST' for x in calls)
