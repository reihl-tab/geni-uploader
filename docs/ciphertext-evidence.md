# Offline ciphertext evidence descriptors, caps and readback

For #257. Pure module `ciphertext_evidence.py`. It follows
`intent-storage-decisions.md` (Decision 2). There is no network access, no
repository writer, no key, no storage service and no gate change. Tests use
synthetic bytes only.

## What it checks

- **Descriptor:** exact keys, schema `geni-evidence-ciphertext-v1`, and a known
  stage (`pre_write`, `acknowledgment`, `readback`, `reconciliation`). It also
  carries:
  - the SHA256 (64 lowercase hex);
  - the exact byte length, 1 byte to 1 MiB;
  - the recipient fingerprint and operation binding (64 hex each);
  - the run ID, with run attempt 1;
  - the git blob ID and commit (40 hex each);
  - `production_enabled` False.
- **Bytes:** the supplied local bytes must match the length, the SHA256 and the
  git blob ID exactly. Empty, oversize and plaintext-shaped bytes are rejected.
  Plaintext-shaped means a JSON/XML/PEM/PDF/ZIP/BOM prefix, or mostly printable
  UTF-8 text.
- **Accounting:** an immutable per-operation ledger, bound to one exact
  operation, run and recipient.
  - Objects are only ever added.
  - Duplicate or conflicting objects (same SHA256 or blob ID) are rejected.
  - The running total is checked against the 8 MiB operation cap.
- **Readback:** the read-back bytes must pass the byte checks, and the remote
  commit must equal the descriptor's commit exactly.
  - The result is fixed: `content_consistent: true`, `ciphertext_proved: false`,
    `retention_proved: false`, `authority: false`.

## What it does not prove

It does not prove that the bytes are real ciphertext, that the recipient can
decrypt them, that the object is privately retained remotely, who uploaded it,
or any authority. Header screening is not proof of encryption or of the
correct recipient. Upload acknowledgment or metadata alone is not readback.

A failure after intent keeps the consumed or uncertain state. It never leads to
a retry, reset, delete or merge, and never falls back to plaintext. The 1 MiB
and 8 MiB caps are candidates that still need reviewed real-schema and
encryption-overhead validation before release.
