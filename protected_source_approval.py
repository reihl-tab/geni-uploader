"""Protected source container envelope. No Geni client and no dispatch capability."""
import datetime
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

IMAGE = 'ghcr.io/reihlinstinct/geni-uploader@sha256:2fa466f87e549d03a0a3e406047e3c733d1efdb582956c066b9530576c96c254'
REPO = 'reihlinstinct/geni-uploader'
WORKFLOW = '.github/workflows/protected-source-approval.yml'


class Blocked(Exception):
    """Fixed boundary failure, never include external values in public output."""


def require(value):
    if not value:
        raise Blocked()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def configuration(raw, digest):
    c = json.loads(raw)
    require(type(c) is dict and set(c) == {'schema', 'private_repo_url', 'private_ref',
            'private_expect_sha', 'manifest_path', 'recipient'})
    require(type(c['schema']) is int and c['schema'] == 1)
    require(hashlib.sha256(canonical(c)).hexdigest() == digest)
    for key in set(c) - {'schema'}:
        require(type(c[key]) is str)
    require(re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.git', c['private_repo_url']))
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]{0,160}', c['private_ref'])
            and '..' not in c['private_ref'] and not c['private_ref'].endswith('/'))
    require(re.fullmatch(r'[a-f0-9]{40}', c['private_expect_sha']))
    require(re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+\.ya?ml', c['manifest_path'])
            and '..' not in c['manifest_path'])
    require(re.fullmatch(r'age1[0-9a-z]{58}', c['recipient']))
    return c


def title(mode, digest, executor):
    return 'protected-sources:' + mode + ':' + digest + ':' + executor


def validate(env, get, clock):
    for key, value in (('GITHUB_REPOSITORY', REPO), ('GITHUB_EVENT_NAME', 'workflow_dispatch'),
                       ('GITHUB_REF', 'refs/heads/master'), ('GITHUB_ACTOR', 'reihlinstinct'),
                       ('GITHUB_TRIGGERING_ACTOR', 'reihlinstinct'), ('GITHUB_RUN_ATTEMPT', '1')):
        require(env.get(key) == value)
    executor = env.get('SOURCE_EXECUTOR_SHA', '')
    digest = env.get('SOURCE_CONFIG_SHA256', '')
    require(re.fullmatch(r'[a-f0-9]{40}', executor) and executor == env.get('GITHUB_SHA'))
    require(re.fullmatch(r'[a-f0-9]{64}', digest))
    mode = env.get('SOURCE_MODE')
    require(mode in ('plan', 'run'))
    require(env.get('SOURCE_CONFIRM') == ('PLAN_SOURCES' if mode == 'plan' else 'UPLOAD_SOURCES'))
    c = configuration(env.get('SOURCE_PACKAGE_JSON', ''), digest)
    run_id = env.get('GITHUB_RUN_ID', '')
    require(re.fullmatch(r'[1-9][0-9]{0,19}', run_id))
    current = get('actions/runs/' + run_id)
    require(current['head_sha'] == executor and current['event'] == 'workflow_dispatch'
            and current['run_attempt'] == 1 and current['actor']['login'] == 'reihlinstinct'
            and current['triggering_actor']['login'] == 'reihlinstinct'
            and current['path'] == WORKFLOW and current['head_branch'] == 'master'
            and current['display_title'] == title(mode, digest, executor))
    protection = get('environments/father-create')
    require(protection['can_admins_bypass'] is False
            and protection['deployment_branch_policy'] == {'protected_branches': False, 'custom_branch_policies': True})
    rule = next(x for x in protection['protection_rules'] if x['type'] == 'required_reviewers')
    require(rule['prevent_self_review'] is True and len(rule['reviewers']) == 1
            and rule['reviewers'][0]['reviewer']['login'] == 'reihl')
    branches = get('environments/father-create/deployment-branch-policies')
    require(branches['total_count'] == 1 and branches['branch_policies'][0]['name'] == 'master'
            and branches['branch_policies'][0]['type'] == 'branch')
    prior_id = env.get('SOURCE_PLAN_RUN_ID', '')
    if mode == 'plan':
        require(not prior_id)
    else:
        require(re.fullmatch(r'[1-9][0-9]{0,19}', prior_id) and prior_id != run_id)
        prior = get('actions/runs/' + prior_id)
        require(prior['status'] == 'completed' and prior['conclusion'] == 'success'
                and prior['event'] == 'workflow_dispatch' and prior['run_attempt'] == 1
                and prior['actor']['login'] == 'reihlinstinct'
                and prior['triggering_actor']['login'] == 'reihlinstinct'
                and prior['head_sha'] == executor and prior['head_branch'] == 'master'
                and prior['path'] == WORKFLOW and prior['workflow_id'] == current['workflow_id']
                and prior['display_title'] == title('plan', digest, executor))
        at = datetime.datetime.fromisoformat(prior['updated_at']).timestamp()
        require(0 <= clock() - at <= 86400)
    return c, mode


def github_get(token, path):
    require(path.startswith(('actions/runs/', 'environments/father-create')))
    request = urllib.request.Request('https://api.github.com/repos/' + REPO + '/' + path,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json'})
    # Fixed GitHub host/path; no redirect forwarding of credentials.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args):
            raise Blocked()
    with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
        return json.loads(response.read(2_000_000))


def command(c, mode, temp):
    args = ['docker', 'run', '--rm', '--tmpfs', '/work',
            '-v', str(temp / 'tree-token') + ':/run/gh-token:ro',
            '-v', str(temp / 'geni-token') + ':/run/geni-token:ro',
            '-e', 'GH_TOKEN_FILE=/run/gh-token',
            '-e', 'GENI_UPLOAD_REPO=' + c['private_repo_url'],
            '-e', 'GENI_UPLOAD_REF=' + c['private_ref'],
            '-e', 'GENI_UPLOAD_EXPECT_SHA=' + c['private_expect_sha']]
    if mode == 'plan':
        args += ['-v', str(temp / 'plan') + ':/run/plan-report',
                 '-e', 'GENI_PLAN_REPORT=/run/plan-report/report.json']
    args += [IMAGE, '--token-file', '/run/geni-token', mode, '--manifest', c['manifest_path']]
    if mode == 'run':
        args += ['--confirm', 'YES']
    return args


def execute(env, get, clock, call=subprocess.run):
    c, mode = validate(env, get, clock)
    temp = Path(env['SOURCE_TEMP'])
    require(temp.is_absolute() and not temp.exists())
    temp.mkdir(mode=0o700)
    (temp / 'plan').mkdir(mode=0o700)
    (temp / 'encrypted').mkdir(mode=0o700)
    for name, key in (('tree-token', 'SOURCE_TREE_PAT'), ('geni-token', 'GENI_ACCESS_TOKEN')):
        require(bool(env.get(key)))
        (temp / name).write_text(env[key]); (temp / name).chmod(0o600)
    # Encryption preflight before any source access; also guarantees age exists.
    call(['age', '-r', c['recipient'], '-o', str(temp / 'encrypted/preflight.age')],
         input=b'protected source encryption preflight', check=True, capture_output=True)
    status = 1
    try:
        with (temp / 'raw.log').open('wb') as log:
            status = call(command(c, mode, temp), stdout=log, stderr=subprocess.STDOUT,
                          check=False).returncode
    finally:
        # Encryption failures are fatal, never leak captured output to public logs.
        for source, dest in ((temp / 'raw.log', 'source-output.age'),
                             (temp / 'plan/report.json', 'source-plan.age')):
            if source.is_file():
                call(['age', '-r', c['recipient'], '-o', str(temp / 'encrypted' / dest), str(source)],
                     check=True, capture_output=True)
    require(status == 0)
    return True


def main():
    try:
        env = os.environ
        execute(env, lambda path: github_get(env['GITHUB_TOKEN'], path), time.time)
        print('source operation complete; inspect encrypted evidence before any further approval')
        return 0
    except Exception:  # noqa: BLE001 - external content never reaches public output
        print('source operation stopped; inspect encrypted evidence; no retry')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
