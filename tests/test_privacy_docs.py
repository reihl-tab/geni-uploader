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


def test_callback_is_static_no_collection_fallback():
    page = (ROOT / 'docs/oauth-callback.html').read_text()
    assert 'layout: null' in page
    assert "history.replaceState(null, '', location.pathname)" in page
    assert 'name="referrer" content="no-referrer"' in page
    assert "default-src 'none'" in page
    for forbidden in ('location.search', 'location.hash', 'document.cookie',
                      'localStorage', 'sessionStorage', 'fetch(', 'XMLHttpRequest',
                      '<form', '<iframe', '<img', 'src=', 'href=', 'console.'):
        assert forbidden not in page
    assert 'does not complete a login or collect a token' in page
    assert 'JavaScript is off' in page
