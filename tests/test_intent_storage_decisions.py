"""Decision-record consistency only, not implementation or live authority."""
from pathlib import Path

import pytest

TEXT = (Path(__file__).resolve().parents[1] / 'docs/intent-storage-decisions.md').read_text()


@pytest.mark.parametrize(('section', 'phrases'), [
    ('Decision 1: protected job, immutable private approval record',
     ['Do not create a new approval signing key/service', 'not owner consent',
      'remains a release blocker', 'No automatic interpretation of chat approval phrases']),
    ('Decision 2: bounded ciphertext in existing private data storage',
     ['existing PRIVATE data repository', 'No public artifacts', 'No new object-store account',
      '1 MiB ciphertext per object and 8 MiB cumulative ciphertext',
      'Read back the remote blob and verify digest', 'No plaintext fallback']),
    ('Permanent intent is independent', ['Permanent owner-global consumption',
                                        'never clears intent', 'No retry, refresh, delete, merge']),
    ('Free-only execution boundary and tradeoffs', ['private Actions', 'STOP and ask',
                                                  'Free allowance is not a hard no-spending guarantee']),
    ('Remaining release work', ['exact private father payload/risk/run approval',
                               'This record supplies none of these permissions']),
])
def test_each_decision_keeps_its_own_boundary(section, phrases):
    part = ' '.join(TEXT.split('## ' + section + '\n', 1)[1].split('\n## ', 1)[0].split())
    for phrase in phrases:
        assert phrase in part, (section, phrase)
