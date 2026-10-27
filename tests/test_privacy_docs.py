"""Public policy copies stay consistent and distinguish conditional modes."""
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_privacy_copies_match_and_cover_hosted_data():
    policy = (ROOT / 'PRIVACY.md').read_text()
    assert policy == (ROOT / 'docs/privacy.md').read_text()
    for required in ('Local mode', 'Hosted GitHub Actions mode',
                     'Separately agreed assistance or token custody',
                     'Raw output can include', 'Git history',
                     'Removing an Actions secret does not',
                     'This is not implied by app registration'):
        assert required in policy
    assert 'The author collects no data' not in policy
    assert 'logs contain timestamps, steps, HTTP statuses and short' not in policy


def test_landing_links_terms_and_privacy_without_authorizing_access():
    landing = (ROOT / 'docs/index.md').read_text()
    assert '[Privacy Policy](privacy.md)' in landing
    assert '[Terms of use](terms.md)' in landing
    terms = (ROOT / 'docs/terms.md').read_text()
    assert 'do not create an account' in terms
    assert '[Privacy Policy](privacy.md)' in terms
    assert 'Geni' in terms and 'GitHub' in terms


def test_callback_is_client_side_fragment_only_with_pinned_script():
    import base64
    import hashlib
    import re
    page = (ROOT / 'docs/oauth-callback.html').read_text()
    assert 'layout: null' in page
    assert "history.replaceState(null, '', location.pathname)" in page
    assert 'name="referrer" content="no-referrer"' in page
    assert "default-src 'none'" in page
    script = re.search(r'<script>(.*?)</script>', page, re.DOTALL).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert "script-src 'sha256-" + digest + "'" in page
    for forbidden in ('location.search', 'document.cookie', 'localStorage',
                      'sessionStorage', 'fetch(', 'XMLHttpRequest', '<form',
                      '<iframe', '<img', 'src=', 'href=', 'console.', 'innerHTML'):
        assert forbidden not in page
    assert "new URLSearchParams(location.hash.slice(1))" in script
    assert "fields.get('access_token')" in script
    assert 'navigator.clipboard.writeText(output.value)' in script
    assert "output.value = ''" in script
    assert 'Never paste it into chat' in page
    assert 'Clipboard history' in (ROOT / 'PRIVACY.md').read_text()


def test_callback_script_extracts_only_fragment_copies_and_clears():
    import json
    import re
    import shutil
    import subprocess

    import pytest
    node = shutil.which('node')
    if not node:
        pytest.skip('node unavailable for offline DOM simulation')
    page = (ROOT / 'docs/oauth-callback.html').read_text()
    script = re.search(r'<script>(.*?)</script>', page, re.DOTALL).group(1)
    harness = r'''
const vm = require('node:vm');
const assert = require('node:assert/strict');
(async () => {
  for (const found of [true, false]) {
    const elements = Object.fromEntries(['token','copy','clear','status'].map(id =>
      [id, {value:'', hidden:true, textContent:'', handlers:{},
        addEventListener(k, fn) {this.handlers[k]=fn;}, focus(){}, select(){}}]));
    const events = [];
    const ctx = {URLSearchParams,
      location:{hash:found?'#access_token=ZZtoken%26value&expires_in=99':'#error=denied', pathname:'/callback.html'},
      history:{replaceState(a,b,c){events.push(c);}},
      navigator:{clipboard:{async writeText(value){events.push(value);}}},
      document:{getElementById(id){return elements[id];},
        addEventListener(k,fn){assert.equal(k,'DOMContentLoaded');fn();}}};
    vm.runInNewContext(SCRIPT, ctx);
    assert.equal(events[0], '/callback.html');
    assert.equal(elements.token.value, found?'ZZtoken&value':'');
    assert.equal(elements.copy.hidden, !found);
    if (found) {
      await elements.copy.handlers.click();
      assert.equal(events[1], 'ZZtoken&value');
      elements.clear.handlers.click();
      assert.equal(elements.token.value, '');
      assert.equal(elements.copy.hidden, true);
    }
  }
})();
'''.replace('SCRIPT', json.dumps(script))
    subprocess.run([node, '-e', harness], check=True, capture_output=True, text=True)
