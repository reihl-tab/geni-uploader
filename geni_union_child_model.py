"""One-child experimental policy; common proofs and consumed marker stay unchanged."""
import geni_protected_household_model as shared_model
from geni_uploader.core.people import require

# Re-export proof primitives used by the scoped IO. No mutable policy globals.
shared = shared_model.shared
vendor_payload = shared_model.vendor_payload
profile_check = shared_model.profile_check
union_check = shared_model.union_check


def plan(value):
    c = shared_model.plan(value)
    require(c['mode'] == 'child' and len(c['entries']) == 1
            and c['accept_omitted_union_fields'] is False)
    return c


def execute(value, io, store, save, clock):
    # Shared marker deliberately unchanged: expiry, union or executor changes do
    # not reopen a consumed named operation from another household workflow.
    return shared_model.execute(plan(value), io, store, save, clock)
