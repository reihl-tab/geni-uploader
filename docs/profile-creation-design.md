# New-profile creation: parent-only phase 1

Version: 0.4, 2026-10-27. Status: design only, not implemented or enabled.
This replaces versions 0.2 and 0.3 in full. No live API calls or test writes.

## Goal and roles

Prepare a bounded user-run addition of at most two parents to the tree owner's
own existing profile. The tree owner approves facts and their storage; the human
operator triggers the tool under that authority. An operator is not automatically
the owner. Both must be named in the private approval record. All public examples
use synthetic ZZ-prefixed names. No family data belongs in this public repository.

Phase 1 permits stable per-entry local IDs for state bookkeeping, but excludes local-ID anchors, other relations, dates/events, profile edits,
merges, photos, email/invitations, deletion and automatic name-match reconciliation.
Those features require separate design and review, not a schema flag or force mode.

## Current source evidence and release blockers

Read without accounts or tokens:
- https://www.geni.com/platform/developer/help/api?path=profile/add-parent
  documents POST creating and returning a parent; names, gender, is_alive and
  public are writable. It does not specify union/slot selection.
- https://www.geni.com/platform/developer/help/api?path=profile/immediate-family
  documents focus and nodes, not completeness or hidden-parent behavior.
- https://www.geni.com/platform/developer/help/api?path=union
  documents partners, children and adopted/foster subsets.
- https://www.geni.com/platform/developer/help/api?path=profile
  documents profile fields including identity, names, public and is_alive.
- https://www.geni.com/platform/developer/help/api?path=user
  documents name/account_type, not the token's own profile identifier.
- https://tamurajones.net/TheGeniModel.xhtml explains historical union edges;
  it is not proof of current response completeness or mutation semantics.

The following are implementation/release blockers, not facts to fake in tests:
1. How to obtain an authoritative token-self profile ID (not name-only /user),
   normalize node versus GUID and prove equality to the declared owner.
2. How to prove the complete parent set, including hidden/inaccessible parents.
   Missing nodes, wrappers or unions are not proof that no parents exist.
3. add-parent behavior with zero, one and two existing parents; how a second
   call selects the existing union; whether gender controls a slot; adopted,
   foster and multiple-parent-union behavior. Do not assume two calls form a couple.
4. Whether public:false is honored and returned for living AND deceased profiles,
   and whether omitted/read-protected fields can be distinguished from false.

Until resolved from documentation or a separately authorized human-observed
response, production writing remains disabled. Synthetic graph/transport code can
be built offline with explicit fixture assumptions, but cannot prove vendor behavior.
No production probe by an agent. public:true is never sent, so whether the vendor
rejects it does not relax this tool's private-only policy.

## Manifest contract

schema_version: 1. Exact keys, bounded strings, no unknown API fields. Owner ref
and expect_name identify the existing root. Two or fewer entries, each relation
parent and anchor equal to that owner; per-entry local IDs identify journal entries only and cannot be anchors; no graph sorting is needed.
Each entry has stable local id, supplied name fields, gender, explicit boolean
is_alive, requested_by_owner:true and private_storage_approved:true. Record the
source and date of the owner's approvals privately, never infer flags. The operator
copies approved values; the tool validates but never creates permission.

Unknown living status fails validation, not a living default. No guessed dates,
surnames, transliterations or maiden name. Payload permits reviewed name fields,
gender, is_alive and fixed public:false only. No data about living people appears
in public logs. Public output is fixed counts/statuses only, not even local IDs.

## Validate, plan and run

- people-validate: local-only schema checks. No token/network, no readiness claim.
- people-plan: read-only remote checks, no state mutation or Geni write. Resolve
  token-self ID, declared owner and anchor to the SAME canonical node ID, and
  verify expect_name. Name alone cannot establish owner identity. Reject merges,
  redirects/ambiguous forms, malformed/hidden family responses or other roots.
- Derive parent relationships from a complete immediate-family graph and verified
  union children/partners, not display relationships or surnames. If slot semantics
  are established, compute free slots and refuse more entries than free slots.
  Existing possible matches block for human review, never auto-skip. Multiple
  unions, unknown gender-to-slot mapping or uncertain empty slots stop the plan.
- A private local plan receipt contains creation time, expiry (15 minutes),
  manifest/schema digest, canonical owner/anchor IDs, every exact payload hash,
  state-ref head and complete parent-set fingerprint. Canonical JSON SHA256 binds
  ALL these selections. It contains no token. Store mode0600 on the operator's
  machine; do not publish it or use a CI artifact. No future-time or expired receipt.
- Phase 1 people-plan and people-run are local-operator-only CLI commands, not
  Actions dispatches. The private receipt stays on that same operator machine;
  there is no CI artifact transfer or cross-run receipt transport. Any later
  Actions version needs a separate reviewed receipt/authentication design.
- people-run requires receipt hash, matching confirm-count and cap<=2. Recompute
  digest and independently repeat account, names, slots, graph, private repo and
  state checks immediately before every POST. Receipt changes/expiry or changed
  parent set require a new plan and approval. The receipt binds the initial plan-time state head. Run must start at that
  head; thereafter each verified intent/ack/result commit is a recorded expected
  descendant within this run. Unknown remote changes still stop. A later parent created by this same
  run is tracked as a verified expected graph delta, not an unexplained change.
- Readback verifies every sent field, public:false, is_alive, gender and actual
  parent relationship. A missing field is unverifiable, not a default success.

```mermaid
flowchart TD
  V[Local validate] --> P[Read-only plan]
  P --> G{All identities, slots and privacy verified?}
  G -->|no| S[Stop, no writes]
  G -->|yes| R[Private expiring plan receipt]
  R --> H[Human confirms count and proposal]
  H --> C[Repeat preconditions and persist intent]
  C --> D{Remote intent commit confirmed?}
  D -->|no| S
  D -->|yes| W[POST once]
  W --> A[Persist acknowledged ID]
  A --> B[GET fields and parent relationship]
  B -->|unverifiable| U[Stop, no blind retry]
  B -->|verified| N[Persist verified result]
```

## Durable state and git branches

Data are read from an immutable reviewed data SHA. State commits go ONLY to an
explicit dedicated state branch, never protected main/default or the data branch.
The user provisions a writable private state ref. No fallback to another branch,
admin push or force push. Verify repository private via authenticated GitHub read.

Under exclusive local flock and a single remote-state writer, fetch state head,
require exact expected SHA and validate strict journal schema/manifest hash.
The first expected SHA is the receipt-bound plan-time state head; each later
expected SHA is the last independently fetched and confirmed commit from this run. Path
must stay within that checkout: refuse symlinks, traversal, unexpected dirty files
and mismatched manifest. Atomically replace and fsync file and parent directory.
Before POST, commit/push an intent containing payload hash and operation ordinal.
Fetch remote ref independently and require exact equality to the intended commit
SHA, not push exit0 or an ancestor check. Non-fast-forward/concurrent changes,
protected-branch rejection, missing git identity or any durability error mean STOP
before POST. No rebase/merge/force during a run.

After POST acknowledgement, save/commit/push returned ID before verification.
After verification, persist verified state. Error, 429, timeout or kill always
stops. An intent without acknowledged ID blocks later creation, including a kill
between intent push and POST. An acknowledged ID permits GET-only verification,
never another create. No error text or credentials in commits or public output. Fixed diagnostic
phases, payload hashes, acknowledged IDs and reviewed resolutions live only in the
private state-branch journal; the private local receipt records plan-time checks.
There is no separate raw response dump or public diagnostic artifact.

## Manual uncertain-intent procedure

There is no edit that resets an uncertain entry to not_started. The owner/operator
checks Geni manually, retaining private dated evidence and the exact manifest hash,
intent commit, operation and anchor. If a created profile is found, a separate
reviewed resolution record may bind its confirmed ID to that intent; the tool
then performs GET-only field/relationship verification. Ambiguous matches stop.

If no profile is found, absence alone does not prove the POST failed. The intent
remains blocked, even if it was likely never sent. Any later retry is a new,
separately reviewed proposal with explicit duplicate risk and a new operation ID;
phase 1 supplies no command to authorize or execute that retry. Never delete the
journal or reuse its ID to make an old create runnable. Preserve all audit history.

## Scope, token and Terms

A dedicated operator token file and explicit repo/ref/SHA selection isolate this
mode. Never switch existing source defaults or another user's token. Agents do
not mint tokens, call Geni with them, trigger workflows or use them for probes.
Secure credential custody, if separately approved, is not permission for live
account use; a claim that agents never hold any token would conflict with the
optional custody arrangement and is deliberately not made here. No token in git,
logs, plan receipts or artifacts. The human operator completes OAuth and runs it.
Geni's restrictions still apply; an API endpoint or human trigger does not prove
compliance. No promise that the token is technically limited to one tree.

No automated rollback or documented delete API. The user checks available manual
UI correction/deletion options. Do not promise undo removes history or links.

## Offline test and release gates

Only synthetic ZZ-prefixed data and loopback fake servers, with the existing
production/E2E boundary. Tests cannot settle the API blockers listed above.
- Missing flags/unknown living status, extra fields/relations, >2 people, local
  anchors, changed schema or digest, expired/future receipt and wrong token owner.
- Zero/one/two parents, second-parent same-union expectations, hidden/partial
  graph, duplicate ambiguity, multiple unions and gender/slot uncertainty.
- Every sent field/private readback, missing field, node/GUID ambiguity, merged IDs.
- Intent push rejection on protected ref, remote SHA race, public repo, dirty tree,
  state symlink/traversal, manifest change and concurrent writers.
- Kill/error at each fsync/push/POST/ack/readback boundary, 429, malformed response,
  receipt expiry midrun, acknowledged GET-only resume and blocked unknown intent.
- Negative/mutation tests for every permission, identity, count and no-retry guard;
  no secret/name/ID/URL/exception leakage on any path.

Both exact-head full-diff reviews, every finding resolved, green CI and separate
human Approve precede merge. Implementation PR adds schema docs, minor version,
CHANGELOG and coverage>=80%. Image build/review/digest pin and isolated workflow
wiring are separate release work. No feature enablement or run from this design.
