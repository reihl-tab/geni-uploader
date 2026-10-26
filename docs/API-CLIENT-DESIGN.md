# API client coverage and offline MCP companion: design

Status: design, slice 1 of the #93 plan. Reviewed scope (2026-10-26):
**offline slices 1-3 only**, MCP **read-only first**. Nothing in this
document authorizes live Geni calls, credentials, workflow dispatch, a write
surface in the MCP server, or edits to the byte-synced `geni_upload.py`.

Code references are to `master` at `cbeea03` and name the function as well
as the line, so they survive line drift.

## Evidence labels

| Label | Meaning |
|---|---|
| **[repo]** | Verified in this repository at `cbeea03`, with a file/line reference. |
| **[repo-doc]** | Stated in an in-repo doc that cites Geni documentation inspected earlier. Not re-inspected for this design. |
| **[model]** | From general knowledge of the Geni v1 API. Unverified; not a source. |
| **[live-gap]** | Needs user-run evidence before anyone relies on it. Dated; a gap is never permission to probe. |

## 1. Endpoint coverage inventory

### 1a. Used today [repo]

Every call goes through `execute()` (`geni_upload.py:244`), which enforces
`ALLOWLIST` (`geni_upload.py:52-58`). `source_details.main()` widens it at
runtime (`source_details.py:429-430`). `API_BASE` must be production, or
loopback with `GENI_UPLOAD_E2E=1` (`geni_upload.py:41-51`).

| Allowlist kind | Method + path | Call sites | Guard | Offline tests |
|---|---|---|---|---|
| `user` | GET `/user` | `whoami` (`geni_upload.py:658`) | Shape-only diagnostic | `test_geni_upload.py` |
| `user_managed_profiles` | GET `/user/managed-profiles` | `contrast` (`:740`), `guidmap` (`:1180`) | Page-bounded | `test_geni_upload.py` |
| `profile` | GET `/profile-{id}`, `/profile-g{guid}`, `/profile?ids=` | `verify_profile` (`:402`), `contrast` (`:755`); `source_details.py:97`, `:386` | Identity + name check; empty bulk result never means "absent" | yes |
| `profile_documents`, `profile_photos` | GET `/profile-{node}/{documents,photos}` | `list_tagged` (`:485`), `listing-shape` (`:1359`) | Same-endpoint `next_page`; 10-page cap returns "unproven" | `test_listing_shape.py`, `test_object_id_readback.py` |
| `document_add`, `photo_add` | POST `/{kind}/add` | `:878` | Intent journaled first; never replayed; non-numeric id raises `UncertainWrite` | yes |
| `document_tag`, `photo_tag` | POST `/{kind}-{oid}/tag/profile-{node}` | `:910`; `source_details.py:250` | Intent before POST; readback by exact object id | yes |
| `document`, `photo` | GET `/{kind}-{oid}` | `object_read` (`source_details.py:79`) | Returned id must equal `{kind}-{oid}` | **document only** |
| `document_update`, `photo_update` | POST `/{kind}-{oid}/update` | `source_details.py:237`, `:352` | Precondition re-read, readback, tags preserved | **document only** |

Gap closed by slice 2: GET `photo` and POST `photo_update` have no offline
test (`grep photo_update tests/` is empty at `cbeea03`).

`auth-url` builds a browser OAuth URL locally and makes no API call
(`geni_upload.py:1125-1139`).

### 1b. Documented or known surface not used

| Area | Operations | Basis | Class |
|---|---|---|---|
| Profile relations | `add-child`, `add-parent`, `add-partner`, `add-sibling` | [repo-doc] `docs/profile-creation-design.md` | Write; out of scope here (#68) |
| Profile reads | `immediate-family`, `unions` | [model] | Read candidate, **unwired/mock-only** (section 2.5) |
| Union | GET `union-{id}` | [model] | Read candidate, unwired/mock-only |
| Search | profile search | [model] | Read candidate; privacy-sensitive; not planned |
| Document/photo | `untag`, `delete` | [repo-doc] `docs/source-details-design.md` excludes them | **Never allowlisted** |
| Fact citations | none known | [repo] `snapshot()` writes `"citations": "unsupported"` (`source_details.py:393`) | Unsupported; not promised |

Every [model] row stays `unverified` until a public-safe documentation excerpt
or a user-run observation confirms it.

### 1c. Live-service gaps (as of 2026-10-26, unverified)

- **[live-gap]** Listing shape: the listing-shape run output is pending with
  the genealogy track. Not inferred here.
- **[live-gap]** `next_page`: absolute vs. relative, and whether `next` ever
  co-occurs. The code accepts both and rejects a conflict (`:487-491`).
- **[live-gap]** `immediate-family`: full profiles or ids only.
- **[live-gap]** GET `photo` / `photo_update` response shape.
- **[live-gap]** Meaning of `X-API-Rate-*` headers on non-429 responses
  (`:228-241`).

No live run is requested by this document. Requests, if any, go through
Instinct per the user-run evidence protocol on #93.

## 2. Offline MCP companion (read-only)

### 2.1 Versioned contract (fixed before choosing an implementation)

The server is an MCP server over **stdio**, so compatibility means the MCP
lifecycle, not bare JSON-RPC.

| Element | Contract |
|---|---|
| Transport | stdio; newline-delimited JSON-RPC 2.0 messages; nothing but protocol messages on stdout; diagnostics on stderr, value-free |
| Version negotiation | `initialize` carries the client's `protocolVersion`. The server answers with the same version if it supports it, otherwise with the newest version it supports. The supported list is a constant, pinned by a test. |
| Capabilities | Server declares `tools` only (`listChanged: false`). No `resources`, `prompts`, `sampling`, `logging` or `roots` in v1. |
| Lifecycle | Requests other than `initialize` and `ping` before `notifications/initialized` get an error. EOF on stdin ends the process with exit 0. No background threads. |
| `tools/list` | Static list; each tool has a name, description and JSON Schema `inputSchema` with `additionalProperties: false`. |
| `tools/call` | Unknown tool or schema-invalid arguments: JSON-RPC error `-32602`. A tool that runs but refuses (path outside the root, limit exceeded): a normal result with `isError: true` and a fixed, value-free message code. |
| Errors | Parse error `-32700`, invalid request `-32600`, unknown method `-32601`, invalid params `-32602`, internal `-32603`. Error data never echoes input values. |
| Compatibility test | A test drives the server through `initialize` → `notifications/initialized` → `tools/list` → `tools/call` → EOF using a real MCP client. If the pinned `mcp` SDK is not a dev dependency yet, the test is marked pending, never presented as executed. |

**Implementation choice comes after this contract.** Options: stdlib-only
(no supply-chain surface, but compatibility must be proven by the client test)
or the official `mcp` SDK, pinned with hashes. The decision is deferred to
slice 5 and needs review; slices 1-3 do not depend on it.

### 2.2 Architecture

- New package `geni_offline/`: pure functions plus the server module.
- It **imports neither `geni_upload` nor `source_details`**: importing them
  loads `execute()` and a mutable module-global `ALLOWLIST` that
  `source_details` widens at runtime. Parity with the CLI comes from tests that
  run both on the same synthetic fixtures. `geni_upload.py` is not edited.
- No production API transport exists in `geni_offline/`. Slice 3's harness
  (section 3.3) enforces that by AST and by an audit hook.

### 2.3 Tool surface (read-only)

| Tool | Reads | Output |
|---|---|---|
| `validate_manifest` | one manifest under the root | verdict + value-free error codes |
| `plan_offline` | one manifest | counts and short hashes, as `plan` without a token |
| `dry_run` | manifest + local status/journal | comparison labelled "local-only, not proof" |
| `inspect_journal`, `inspect_status` | one state file | phase counts only |
| `analyze_run_output` | user-supplied sanitized output | parsed categories; malformed input fails closed |

Never reachable: `execute()`, `urllib`, `http.client`, `socket`, `requests`,
`subprocess`; any token-taking CLI mode; any token, env secret or `gh`;
writing, repairing or deleting any file.

**Not authorized:** `draft_manifest`. If it is approved separately later, it
may only create an inert, new, private draft; it never replaces the active
manifest, status or journal, and never promotes or executes anything.

### 2.4 Path confinement

- The root comes from server argv only, never from tool input.
- Access is **descriptor-based**: open the root once as a directory fd, then
  walk each relative component with `os.open(name, O_RDONLY | O_NOFOLLOW |
  O_CLOEXEC, dir_fd=parent_fd)`, requiring `S_ISDIR` for intermediate
  components and `S_ISREG` for the final one (checked with `os.fstat` on the
  opened fd). No `realpath`-then-`open`.
- Rejected before any open: absolute paths, empty components, `.`/`..`, NUL,
  and paths longer than a fixed limit.
- Tests: a symlink at the final and at an intermediate component, a `..`
  escape, an absolute path, and a race where a checked directory is swapped
  for a symlink between calls (must still refuse, because each component is
  opened with `O_NOFOLLOW` relative to an already-open fd).
- Platform: needs `dir_fd` support (Linux, macOS). The server refuses to start
  where `os.open in os.supports_dir_fd` is false.

### 2.5 Read clients

Any client for unused read endpoints (`immediate-family`, `union`) is a
library with a mock transport only. It is not wired to any MCP tool or CLI
mode, and it has no production transport until a separate review.

### 2.6 Startup refusal, redaction and limits

- Refuses to start if `GENI_ACCESS_TOKEN`, `GENI_API_BASE`, `GENI_UPLOAD_E2E`
  or `GH_TOKEN` is set.
- Output has no names, titles, URLs, profile/guid/object ids or file bytes;
  items appear as index plus short hash, the same idea as `label()`
  (`geni_upload.py:87`).
- Bounded parsing: input file ≤ 1 MiB (read at most limit + 1 bytes), JSON/YAML
  depth ≤ 32, ≤ 500 targets, response ≤ 64 KiB with explicit truncation.
  YAML is parsed with the safe loader only.
- All inputs are untrusted data; instructions inside them are ignored.

## 3. Synthetic contract tests (slices 2-3)

### 3.1 Fixtures

`tests/contracts/<kind>/<case>.json`:
`{request: {method, kind, path_template}, response: {status, headers, body},
expect: {outcome, journal_phase?}}`. Invented values only (ids like
`1000001`, the name "Test Person").

### 3.2 Runner and cases (slice 2)

One parametrized runner drives each case through a fake `execute` and the
loopback `HTTPServer` pattern already used in `test_source_details_e2e.py`.
Cases per kind: prefixed vs. bare ids; guid + name match/mismatch; empty
`{"results": []}`; singleton source object; `next_page` chain; cross-endpoint
`next_page` rejected; page cap returns unproven; 429 stops; GET 5xx retries;
POST 5xx/timeout/bad JSON raise `UncertainWrite` with no replay; add without
an id; a failed tag readback never recreates. Plus GET `photo` and
`photo_update`, and a snapshot test that pins the exact `ALLOWLIST` and the
runtime widening in `source_details`, so a new endpoint needs a reviewed test
change.

### 3.3 Zero-network harness (slice 3)

1. AST import scan of `geni_offline/`: forbids `socket`, `ssl`, `http`,
   `urllib`, `requests`, `subprocess`, `ctypes`, `geni_upload`,
   `source_details`, and `__import__`/`importlib` calls.
2. Each tool runs in a child interpreter with `sys.addaudithook` that raises
   on `socket.*`, `urllib.Request`, `subprocess.Popen`, `os.system`,
   `os.exec*` and `os.posix_spawn`.
3. Self-test: a planted `import socket` double makes the scan fail, and a
   planted `socket.socket()` call makes the hook fail.

## 4. Slices

| # | Slice | Status |
|---|---|---|
| 1 | This document | authorized |
| 2 | Contract fixtures + runner + allowlist snapshot + photo coverage | authorized |
| 3 | Zero-network harness with an empty `geni_offline/` | authorized |
| 4 | `validate_manifest`, `plan_offline` with CLI parity tests | needs review |
| 5 | MCP server per section 2.1 (implementation choice decided here) | needs review |
| 6 | `inspect_journal`, `inspect_status` with sentinel-leak tests | needs review |
| 7 | `analyze_run_output` | needs review |
| 8 | `draft_manifest` | **not authorized** |
| 9 | Unwired read-client library | needs review |

Each slice is one PR with focused synthetic tests and an exact-head
independent review before merge.

## 5. Open decisions

1. **Documentation citations:** until public-safe excerpts are posted, every
   unused endpoint stays [model]/unverified.
2. **Implementation of the MCP server:** stdlib vs. pinned SDK, decided in
   slice 5 against the contract in 2.1.
3. **Moving CLI internals onto `geni_offline`:** needs the private-copy owner,
   because `geni_upload.py` is byte-synced. Until then: parity tests only.
