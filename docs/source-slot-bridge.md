# Fixed-slot source credential bridge

Design for #695. A separate protected workflow copies only repository
GENI_SECONDARY_ACCESS_TOKEN to father-create GENI_ACCESS_TOKEN, encrypted
with the destination environment public key inside the GitHub runner.
No Geni calls, OAuth, primary-slot writes, dynamic targets, artifacts or
credential output. Existing connection slots and site mode stay unchanged.

Master-only, exact executor SHA, automation actor/triggering actor and first
attempt required. A fixed confirmation and the existing human deployment
approval are mandatory. The dedicated SOURCE_BRIDGE_WRITER environment secret
must permit reading environment metadata/public key and writing this environment
secret. Its installation is separate authorized setup, never a repository-secret
read. GitHub credentials cannot themselves restrict writes to one named secret;
fixed code destinations and review constrain this operation, not the token scope.

Runtime independently checks run metadata, human reviewer/master/no-bypass
protection, and absence of an environment override for the secondary source
name. A hash-only source updated_at input must match current repository secret
metadata before transfer. The source value is only supplied through Actions'
secret environment injection. It is never printed, persisted or returned.
Destination metadata is verified after one PUT. On uncertain PUT or any error,
stop without retry. Only fixed success/failure text reaches public logs.

Follow bridge with a separately approved source PLAN explicitly naming the
selected account in private communication; then inspect target identity,
listing/duplicates and safe-to-run status. Bridge success does not prove Geni
identity, upload permission or authorize an upload. No upload before its own go.
Tests cover gates, exact paths/destination, sealed-value transport, no plaintext
output and all workflow steps, including no artifact uploads or scripts with
secret interpolation. Independent review and exact-head green CI before merge.
