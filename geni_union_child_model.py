"""One-child experimental policy; common proofs and consumed marker stay unchanged."""
import geni_protected_household_model as shared_model
from geni_uploader.core.people import require

# Re-export proof primitives used by the scoped IO. No mutable policy globals.
shared = shared_model.shared
union_check = shared_model.union_check


def plan(value):
    require(type(value) is dict)
    flag = value.get('accept_first_child_omission', False)
    require(type(flag) is bool)
    base = {key: leaf for key, leaf in value.items() if key != 'accept_first_child_omission'}
    c = shared_model.plan(base, allow_hebrew_only=True)
    require(c['mode'] == 'child' and len(c['entries']) == 1
            and c['accept_omitted_union_fields'] is False)
    if flag:
        members = c['family'][c['target_union']]
        require(len(members) == 2 and set(members.values()) == {'partner'})
    if 'accept_first_child_omission' in value:
        c['accept_first_child_omission'] = flag
    return c


def execute(value, io, store, save, clock):
    # Shared marker deliberately unchanged: expiry, union or executor changes do
    # not reopen a consumed named operation from another household workflow.
    c = plan(value)
    flag = c.pop('accept_first_child_omission', False)
    return shared_model.execute(c, io, store, save, clock, allow_hebrew_only=True,
                                accept_first_child_omission=flag)


def vendor_payload(value):
    return shared_model.vendor_payload(value, allow_hebrew_only=True)


def profile_check(actual, expected, target, allow_unknown, *, created=False):
    return shared_model.profile_check(actual, expected, target, allow_unknown,
                                     created=created, allow_hebrew_only=True)
