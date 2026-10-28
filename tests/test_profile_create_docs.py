"""Documentation consistency, not a test of vendor behavior or release authority."""
from pathlib import Path

from human_parent_gate import require_production_release
from people_core import Blocked


def test_route_inventory_and_limit_statements():
    text = (Path(__file__).resolve().parents[1] /
            'docs/profile-create-api-contracts.md').read_text()
    for method in ('profile/add-parent', 'profile/add-partner', 'profile/add-child',
                   'profile/add-sibling', 'union/add-partner', 'union/add-child',
                   'profile/update', 'union/update', 'profile/merge',
                   'profile/immediate-family'):
        assert 'https://www.geni.com/platform/developer/help/api?path=' + method in text
    for limit in ('HTTP verb not stated', 'Names locale maps not listed',
                  'Existing-profile edit requires exact target/field approval',
                  'Missing merge\nfields stay UNKNOWN',
                  'zero observed parents is not proof of absence',
                  'only the dedicated reviewed reconciliation transition can finish',
                  'No live Geni request was made'):
        assert limit in text
    try:
        require_production_release()
    except Blocked:
        pass
    else:
        raise AssertionError('documentation must not enable production')
