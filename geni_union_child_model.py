"""One-child experimental policy; common proofs and consumed marker stay unchanged."""
import geni_protected_household_model as shared_model
from geni_uploader.core.people import require

# Re-export proof primitives used by the scoped IO. No mutable policy globals.
shared = shared_model.shared
union_check = shared_model.union_check


def plan(value):
    c = shared_model.plan(value, allow_hebrew_only=True)
    require(c['mode'] == 'child' and len(c['entries']) == 1
            and c['accept_omitted_union_fields'] is False)
    return c


def execute(value, io, store, save, clock):
    # Shared marker deliberately unchanged: expiry, union or executor changes do
    # not reopen a consumed named operation from another household workflow.
    return shared_model.execute(plan(value), io, store, save, clock, allow_hebrew_only=True)


def vendor_payload(value):
    return shared_model.vendor_payload(value, allow_hebrew_only=True)


def profile_check(actual, expected, target, allow_unknown, *, created=False):
    return shared_model.profile_check(actual, expected, target, allow_unknown,
                                     created=created, allow_hebrew_only=True)
