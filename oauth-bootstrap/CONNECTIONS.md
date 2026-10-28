# Fixed isolated human OAuth destinations

For #197/#189. Code only, not deployed by this PR. Uses the existing app and
/callback route: no new Geni app/callback, account, paid plan or service is
required by this design. Actual registration/selected provider route must still
be verified before the human starts. No agent executes OAuth or live API calls.

A fixed source registry defines primary, secondary and tertiary. Each destination
has its own fixed access-token and refresh-bundle GitHub secret names. The human
chooses a button before authorization. The destination is stored in one-time
server-side state bound to the authenticated GitHub subject/browser; callback
parameters cannot choose a secret name. Unknown destinations/query selectors and
replays stop. New destination registry entries require a code review/release,
not a runtime string supplied by a caller. Named slots are generic in public code;
the operator privately records which consenting owner occupies each slot.

Enabling any additional owner pin also requires PRIMARY_OWNER_NODE, and all
configured owner pins must be distinct canonical profile-N IDs. SECONDARY_OWNER_NODE
and TERTIARY_OWNER_NODE independently enable those slots. Missing secondary/tertiary
pin stops that selection. Before any secret write in a configured slot, the
human-initiated callback reads token-self from the fixed HTTPS /api/profile route
with bearer header and redirects refused. It requires exact expected ID,
merge_pending:false and no merged_into/results wrapper. Wrong or unprovable
identity stops all writes. Primary is checked too when pins are configured, so
pressing the wrong button while logged into another owner cannot overwrite it.
Legacy primary-only installations without any owner pins retain existing behavior;
that compatibility mode is not safe for multiple connections and is not permission
to deploy an additional route without the pins.

Do not guess owner pins from website GUIDs or name-only matches. Establish the
canonical nodes through authorized human-observed evidence first. Never publish
real owner IDs, access/refresh tokens, app secrets, callback codes or raw responses.
The owner GET validates identity only; it does not prove parent completeness,
private create behavior, consent or plan readiness. It must be understood as part
of the user's deliberately initiated connection, not an agent-initiated probe.

Each slot writes pending refresh bundle, matching access token and finalized
bundle only into that slot. Partial failure stops; pending recovery must be
reviewed for that exact slot. Current upload/refresh workflows still consume ONLY
primary secrets. New secondary/tertiary tokens are NOT automatically usable by
those workflows, and this PR does not wire any upload or parent creation route.
Separate reviewed human-run consumers must select the correct slot and validate
owner again before use. No sharing a primary refresh runner with an additional
slot by renaming arbitrary secrets at runtime.

Deployment needs separate chat approval after independent review/green CI, verified
expected-owner values and existing secret-writer permission scope. No secrets in
commands/URLs/logs/chat. After deployment the human opens the verified landing
page, signs into approved GitHub identity if asked, confirms correct Geni account
and selects the intended slot. Never give the old single-primary connect link to
a second owner before the new deployment/config is verified. Record the actual
callback/route and slot mapping privately and provide one step at a time.
