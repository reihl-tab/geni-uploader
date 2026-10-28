"""Documentation consistency, not a test of vendor behavior or release authority."""
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(('method', 'limits'), [
    ('profile/add-parent', ('No documented existing-profile input', 'parent-slot selector',
                            'idempotency key', 'hidden-parent completeness')),
    ('profile/add-partner', ('Not an existing-ID connector',
                             "does not promise reuse of a particular child's parent union")),
    ('profile/add-child', ("No documented selector for choosing among that profile's unions",)),
    ('profile/add-sibling', ('No documented sibling ordering control',
                             'explicit parent-union selector')),
    ('union/add-partner', ('Names locale maps not listed',
                           'usage shows bare union/add-partner, not an ID',
                           'HTTP verb not stated on this page',
                           'returned-fields table lists union fields despite profile-return prose')),
    ('union/add-child', ('Names locale maps not listed',
                         'usage shows union-1/add-child',
                         'HTTP verb not stated on this page',
                         'returned-fields table lists union fields despite profile-return prose')),
    ('profile/update', ('Existing-profile edit requires exact target/field approval',
                        'does not prove rights, merge-clear state or readback')),
    ('union/update', ('writable parameters listed are marriage and divorce events',
                      'not documented writable inputs',
                      'not a demonstrated connector for two existing profiles')),
    ('profile/merge', ('Sparse contract', 'not a marriage operation',
                       'never use identity merge to connect spouses')),
])
def test_each_method_row_retains_its_own_limits(method, limits):
    text = (Path(__file__).resolve().parents[1] /
            'docs/profile-create-api-contracts.md').read_text()
    prefix = '| [' + method + ']('
    rows = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(rows) == 1
    for limit in limits:
        assert limit in rows[0], (method, limit)
