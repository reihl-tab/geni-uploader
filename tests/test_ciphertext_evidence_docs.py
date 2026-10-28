"""Pin the ciphertext-evidence doc so its limits cannot drift silently (#257)."""
import hashlib
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / 'docs' / 'ciphertext-evidence.md'
# Update deliberately, in the same reviewed PR, whenever the doc changes.
EXPECTED_SHA256 = 'a7cd6812cac5006e8024392df512f0ded36aaef4b759bb7bd8132d1a60eb3478'


def test_ciphertext_evidence_doc_is_pinned():
    assert hashlib.sha256(DOC.read_bytes()).hexdigest() == EXPECTED_SHA256


def test_ciphertext_evidence_doc_states_the_limits():
    text = DOC.read_text(encoding='utf-8')
    for claim in ('`ciphertext_proved: false`', '`retention_proved: false`', '`authority: false`',
                  '1 MiB', '8 MiB', 'never falls back to plaintext'):
        assert claim in text
