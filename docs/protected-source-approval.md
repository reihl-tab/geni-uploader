# Protected source approval workflow

Issue #691. Separate from the unchanged user-only source workflow.

## Contract

Automation dispatches one plan or one upload, each as a new run requiring the
existing master-only protected environment and human reviewer. No bypass,
rerun, schedule, pull-request trigger, automatic upload or retry. Dispatch
inputs contain only mode, executor SHA, configuration SHA256, prior plan run
ID and fixed confirmation. All source identifiers remain in a separate
private environment secret. The existing pinned container is reused; no new
Geni client or token leaves GitHub.

## Immutable package

Private JSON fields: schema, private_repo_url, private_ref, private_expect_sha,
manifest_path and recipient. Canonical JSON SHA256 is the public package pin.
Reject unknown fields, unsafe repository/ref/path/recipient values and missing
pins. Before the container starts, validate automation actor, master, first
attempt, exact executor SHA and package digest. Check the protected environment
still has required human review, prevents self-review, forbids administrator
bypass and allows master only. No environment settings are changed by a run.

## Plan to upload

Plan confirmation is PLAN_SOURCES. Upload confirmation is UPLOAD_SOURCES and
requires a successful prior plan from this separate workflow, first attempt,
same exact executor and package digest, dispatched by the automation account,
within 24 hours. The prior run's fixed hash-only run name binds mode/package;
GitHub run metadata must match. A successful process is necessary, not enough:
the human reviews decrypted identity, listing, duplicate/blocked state and
safe-to-run result before separately approving the upload deployment. Plan
approval never approves upload. A moved source branch fails its exact SHA
check; stop and prepare/review a fresh package and plan. Source status commits
may move the branch after upload; no blind repin or rerun.

## Output and effects

Mount temporary token files read-only, use the existing container's source
loader and exact git SHA check, capture all stdout/stderr privately, and never
publish raw exceptions or identifying values. Encrypt captured output and
plan report to the package recipient, retain encrypted artifacts for one day,
and remove temporary plaintext in an always step. Do not commit log files
back to the source branch: a plan must not invalidate its own data pin.
Container failures still preserve encrypted evidence and fail the job.
Uncertain writes require evidence review, not retry. Source documents only;
no profile edit, details repair, fact changes or invitations in this route.

## Tests

Synthetic tests kill actor/ref/attempt/executor/config/mode/confirmation and
prior-plan identity/hash/age/result gates. Test private values never enter
public output, container image digest is fixed, secrets are not CLI values,
plan/run remain separate human approvals, failed container evidence is
preserved, original user-only workflow is byte-for-byte unchanged, and no
runtime network or dispatch happens in tests. Independent exact-head review
and green CI precede signed normal merge. Live execution still needs exact
owner authority and the human deployment approval.
