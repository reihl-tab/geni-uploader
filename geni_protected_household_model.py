"""Bounded household create model. Injected effects only, no credentials or transport."""
import copy
import re

import bounded_parent_addition as shared
from geni_uploader.core.people import exact, require, text
from one_time_parent_pilot import merge_clear


def new_payload(value):
    require(type(value) is dict)
    exact(value, ('names', *value.get('names', {}).get('en', {}), 'is_alive', 'public',
                  'about_me', *(('gender',) if 'gender' in value else ())))
    names = value['names']
    require(type(names) is dict and set(names) == {'en', 'he'})
    for fields in names.values():
        require(type(fields) is dict and 'first_name' in fields
                and set(fields) <= {'first_name', 'middle_name', 'last_name', 'maiden_name'})
        for leaf in fields.values():
            text(leaf)
    require(all(value[k] == leaf for k, leaf in names['en'].items()))
    require(value['is_alive'] is True and value['public'] is False)
    if 'gender' in value:
        require(value['gender'] in ('male', 'female'))
    # One documented about_me string, Hebrew and English paragraphs, not an invented API locale.
    require(type(value['about_me']) is str and 10 <= len(value['about_me']) <= 4000
            and re.search('[א-ת]', value['about_me']) and re.search('[A-Za-z]', value['about_me']))
    return copy.deepcopy(value)


def vendor_payload(value):
    body = new_payload(value)
    body['names'] = {'he': body['names']['he'], 'en-US': body['names']['en']}
    return body


def existing_payload(value):
    require(type(value) is dict and {'first_name', 'is_alive', 'public'} <= set(value)
            and set(value) <= {'first_name', 'middle_name', 'last_name', 'maiden_name',
                               'gender', 'is_alive', 'public', 'claimed'})
    for key in ('first_name', 'middle_name', 'last_name', 'maiden_name'):
        if key in value:
            text(value[key])
    require(type(value['is_alive']) is bool and type(value['public']) is bool)
    if 'claimed' in value:
        require(type(value['claimed']) is bool)
    if 'gender' in value:
        require(value['gender'] in ('male', 'female'))
    return copy.deepcopy(value)


def graph_spec(value):
    require(type(value) is dict and 1 <= len(value) <= 4)
    for union, members in value.items():
        shared.union_id(union)
        require(type(members) is dict and 1 <= len(members) <= 20
                and 1 <= list(members.values()).count('partner') <= 2)
        for node, role in members.items():
            shared.profile_id(node)
            require(role in ('child', 'partner'))
    return copy.deepcopy(value)


def plan(value):
    exact(value, ('schema', 'mode', 'owner', 'expect_name', 'anchor', 'profiles', 'family',
                  'target_union', 'external_edges', 'entries', 'expires_at', 'allow_unknown_merge',
                  'accept_hidden_duplicate_risk', 'accept_private_create_risk',
                  'accept_union_selection_risk', 'accept_omitted_union_fields'))
    require(type(value['schema']) is int and value['schema'] == 1)
    require(value['mode'] in ('child', 'partner'))
    for key in ('owner', 'anchor'):
        shared.profile_id(value[key])
    require(type(value['expect_name']) is str and 2 <= len(value['expect_name'].split()) <= 8)
    require(type(value['expires_at']) is int and 0 < value['expires_at'] < 2**40)
    require(type(value['allow_unknown_merge']) is bool)
    for key in ('accept_hidden_duplicate_risk', 'accept_private_create_risk',
                'accept_union_selection_risk'):
        require(value[key] is True)
    require(type(value['accept_omitted_union_fields']) is bool)
    family = graph_spec(value['family'])
    members = {p for m in family.values() for p in m}
    require(value['anchor'] in members and type(value['profiles']) is dict
            and set(value['profiles']) == members | {value['owner']}
            and len(value['profiles']) <= 24)
    for node, body in value['profiles'].items():
        shared.profile_id(node)
        existing_payload(body)
    require(type(value['external_edges']) is dict and set(value['external_edges']) <= members
            and value['anchor'] not in value['external_edges'])
    for edges in value['external_edges'].values():
        require(type(edges) is dict and len(edges) <= 4)
        for union, role in edges.items():
            shared.union_id(union)
            require(union not in family and role in ('child', 'partner'))
    target = value['target_union']
    if value['mode'] == 'child':
        shared.union_id(target)
        require(target in family and family[target].get(value['anchor']) == 'partner'
                and list(family[target].values()).count('partner') == 2
                and len(family[target]) + len(value['entries']) <= 20)
    else:
        require(target is None)  # always a new partner union, never replace an existing partner
    entries = value['entries']
    require(type(entries) is list and (1 <= len(entries) <= 4 if value['mode'] == 'child'
                                      else len(entries) == 1))
    keys, names = set(), set()
    for entry in entries:
        exact(entry, ('key', 'payload'))
        require(type(entry['key']) is str and re.fullmatch(r'[a-z][a-z0-9-]{1,48}', entry['key'])
                and entry['key'] not in keys)
        keys.add(entry['key'])
        body = new_payload(entry['payload'])
        name = shared.canonical(body['names'])
        require(name not in names)
        names.add(name)
    return copy.deepcopy(value)


def marker(c, entry):
    # Union/expiry/package changes cannot silently reopen the same named operation.
    return 'household-create-consumed-v1-' + shared.digest({
        'owner': c['owner'], 'anchor': c['anchor'], 'mode': c['mode'],
        'key': entry['key'], 'payload': entry['payload']})


def profile_check(actual, expected, target, allow_unknown, *, created=False):
    require(type(actual) is dict and actual.get('id') == target and 'error' not in actual)
    merge_clear(actual, allow_unknown)
    for key, leaf in (vendor_payload(expected) if created else existing_payload(expected)).items():
        require(actual.get(key) == leaf)
    if created:
        require(actual.get('claimed') is False)


def union_check(actual, target, members, accept_omitted):
    require(type(actual) is dict and actual.get('id') == target and 'error' not in actual
            and not any(k in actual for k in ('next_page', 'paging', 'pagination')))
    unknown = []
    for field, role in (('partners', 'partner'), ('children', 'child')):
        if field not in actual:
            require(accept_omitted)
            unknown.append(field)
            continue
        values = actual[field]
        require(type(values) is list and len(values) <= 20)
        ids = values
        # Actual Geni refs may be canonical API URLs, never arbitrary domains.
        normalized = []
        for node in ids:
            require(type(node) is str)
            m = re.fullmatch(r'(?:https://www\.geni\.com/api/)?(profile-[0-9]{1,30})', node)
            require(m is not None)
            normalized.append(m.group(1))
        require(len(set(normalized)) == len(normalized)
                and set(normalized) == {p for p, r in members.items() if r == role})
    require(actual.get('adopted_children', []) == [] and actual.get('foster_children', []) == [])
    return unknown


def execute(value, io, store, save, clock):
    c = plan(value)
    graph = copy.deepcopy(c['family'])
    target = c['target_union']
    known = set(c['profiles'])
    r = {'schema': 1, 'phase': 'STOPPED', 'mode': c['mode'], 'stage': 'preflight',
         'items': [], 'responses': [], 'unknown_union_fields': [], 'retry_allowed': False,
         'full_visibility': 'UNPROVED', 'merges': False}

    def now():
        require(clock() < c['expires_at'])

    def read(kind, node):
        now()
        r['stage'] = 'read_' + kind
        actual = getattr(io, 'get_' + kind)(node)
        r['responses'].append({'kind': kind, 'target': node, 'value': actual})
        save(copy.deepcopy(r))
        return actual

    def union_read(union):
        missing = union_check(read('union', union), union, graph[union], c['accept_omitted_union_fields'])
        if missing:
            r['unknown_union_fields'].append({'union': union, 'fields': missing,
                                              'state': 'UNKNOWN_OMITTED'})

    try:
        owner = read('profile', 'profile')
        require(owner.get('id') == c['owner'])
        name = ' '.join(owner.get(k, '') for k in ('first_name', 'middle_name', 'last_name'))
        require(all(w.casefold() in name.casefold().split() for w in c['expect_name'].split()))
        for node, body in c['profiles'].items():
            actual = read('profile', node)  # explicit second owner identity GET too
            profile_check(actual, body, node, c['allow_unknown_merge'])
        shared.graph_check(read('family', c['anchor']), c['anchor'], graph,
                           external_edges=c['external_edges'])
        for union in graph:
            union_read(union)
        for entry in c['entries']:
            # Recheck anchor graph immediately before consumption/send, no omitted local edge.
            shared.graph_check(read('family', c['anchor']), c['anchor'], graph,
                               external_edges=c['external_edges'])
            if target:
                union_read(target)
            item = {'key': entry['key'], 'marker': marker(c, entry), 'phase': 'NOT_SENT'}
            r['items'].append(item)
            now(); r['stage'] = 'before'
            store.receipt(item['marker'], 'before', save(copy.deepcopy(r)))
            now(); r['stage'] = 'consume'
            store.consume(item['marker'])
            now(); r['stage'], item['phase'] = 'send', 'UNCERTAIN'
            actual = io.add(c['anchor'], c['mode'], vendor_payload(entry['payload']))
            item['create_response'] = actual
            require(type(actual) is dict and 'error' not in actual)
            created = actual.get('id')
            shared.profile_id(created)
            require(created not in known)
            item.update(id=created, phase='ACKNOWLEDGED_NOT_VERIFIED')
            now(); r['stage'] = 'ack'
            store.receipt(item['marker'], 'ack', save(copy.deepcopy(r)))
            profile_check(read('profile', created), entry['payload'], created,
                          c['allow_unknown_merge'], created=True)
            family = read('family', c['anchor'])
            if c['mode'] == 'partner':
                require(type(family) is dict and type(family.get('nodes')) is dict
                        and len(family['nodes']) <= 30)
                added = {n for n in family['nodes'] if re.fullmatch(r'union-[0-9]{1,30}', n)} - set(graph)
                require(len(added) == 1)
                target = next(iter(added))
                graph[target] = {c['anchor']: 'partner', created: 'partner'}
            else:
                graph[target][created] = 'child'
            shared.graph_check(family, c['anchor'], graph, external_edges=c['external_edges'])
            boundary = shared.boundary_edges({'family': c['family'], 'external_edges': c['external_edges']},
                                            target, graph[target])
            shared.graph_check(read('family', created), created, {target: graph[target]},
                               external_edges=boundary)
            union_read(target)
            # Exact proofs happen before the transport opens another send latch.
            io.verified(created, target, copy.deepcopy(graph))
            known.add(created)
            now(); r['stage'], item['phase'] = 'final', 'VERIFIED'
            store.receipt(item['marker'], 'final', save(copy.deepcopy(r)))
        now(); r.update(phase='VERIFIED', stage='complete')
        save(copy.deepcopy(r))
    except Exception:  # noqa: BLE001 - uncertain effect/storage is terminal, no repair
        r['phase'] = 'STOPPED'
        save(copy.deepcopy(r))
    return r
