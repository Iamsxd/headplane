#!/usr/bin/env python3
"""Private optional-MFA acceptance against the official service. Output booleans only."""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import struct
import time
import urllib.error
import urllib.parse
from importlib.machinery import SourceFileLoader

setup = SourceFileLoader('casdoor_setup', str(Path(__file__).with_name('casdoor-setup.py'))).load_module()
Api, ORIGIN = setup.Api, setup.ORIGIN


def require(condition, name):
    if not condition:
        raise RuntimeError('Acceptance failed: ' + name)


def totp(secret):
    raw = base64.b32decode(secret + '=' * (-len(secret) % 8))
    digest = hmac.new(raw, struct.pack('>Q', int(time.time()) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return str((struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000).zfill(6)


def flow(private):
    verifier = secrets.token_urlsafe(48)
    query = {'clientId': private['client_id'], 'redirectUri': ORIGIN + '/admin/oidc/callback',
        'scope': 'openid email profile', 'state': secrets.token_urlsafe(20), 'nonce': secrets.token_urlsafe(20),
        'code_challenge_method': 'S256',
        'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')}
    return verifier, query


def login(api, private, username, password):
    verifier, query = flow(private)
    body = {'type': 'code', 'signinMethod': 'Password', 'organization': 'headplane',
        'application': 'headplane', 'username': username, 'password': password}
    response = api.request('/api/login?' + urllib.parse.urlencode(query), body)
    return response, verifier, query


def code_ok(response):
    value = response.get('data')
    return response.get('status') == 'ok' and isinstance(value, str) and bool(value) and value not in ['NextMfa', 'RequiredMfa']


def exchange(api, private, code, verifier):
    return api.request('/api/login/oauth/access_token', {'grant_type': 'authorization_code',
        'client_id': private['client_id'], 'client_secret': private['client_secret'], 'code': code,
        'code_verifier': verifier, 'redirect_uri': ORIGIN + '/admin/oidc/callback'}, form=True)


def main():
    admin, private = setup.maintenance()
    username, password = 'acceptance-' + secrets.token_hex(6), secrets.token_urlsafe(32)
    user = {'owner': 'headplane', 'name': username}
    admin.ok('/api/add-user', {**user, 'displayName': 'Disposable acceptance account', 'password': password,
        'type': 'normal-user', 'isAdmin': False, 'signupApplication': 'headplane', 'language': 'zh'})
    results = {}
    try:
        org = admin.ok('/api/get-organization?id=admin%2Fheadplane')
        # get-organization presents a legacy 12-hour default for zero; check the persisted policy.
        with sqlite3.connect('file:/var/lib/casdoor/casdoor.db?mode=ro', uri=True) as db:
            remember = db.execute('SELECT mfa_remember_in_hours FROM organization WHERE owner=? AND name=?', ('admin', 'headplane')).fetchone()[0]
        results['totp_optional_without_remembering'] = org['mfaItems'] == [{'name': 'app', 'rule': 'Optional'}] and remember == 0
        api = Api()
        response, verifier, _ = login(api, private, username, password)
        results['unenrolled_password_login'] = code_ok(response)
        require(results['unenrolled_password_login'], 'unenrolled_password_login')
        tokens = exchange(api, private, response['data'], verifier)
        results['authorization_code_pkce_issues_id_token'] = bool(tokens.get('id_token'))
        common = {**user, 'mfaType': 'app'}
        props = api.ok('/api/mfa/setup/initiate', common, form=True)
        wrong = api.request('/api/mfa/setup/verify', {**common, 'secret': props['secret'], 'passcode': 'invalid'}, form=True)
        results['wrong_enrollment_code_rejected'] = wrong.get('status') != 'ok'
        api.ok('/api/mfa/setup/verify', {**common, 'secret': props['secret'], 'passcode': totp(props['secret'])}, form=True)
        recovery = props['recoveryCodes'][0]
        api.ok('/api/mfa/setup/enable', {**common, 'secret': props['secret'], 'recoveryCodes': recovery}, form=True)
        fresh = Api()
        response, verifier, query = login(fresh, private, username, password)
        results['enrolled_password_requires_factor'] = response.get('data') == 'NextMfa'
        common_login = {'type': 'code', 'organization': 'headplane', 'application': 'headplane', 'mfaType': 'app'}
        route = '/api/login?' + urllib.parse.urlencode(query)
        results['missing_factor_rejected'] = not code_ok(fresh.request(route, common_login))
        results['wrong_factor_rejected'] = not code_ok(fresh.request(route, {**common_login, 'passcode': 'invalid'}))
        response = fresh.request(route, {**common_login, 'passcode': totp(props['secret'])})
        results['valid_totp_login'] = code_ok(response)
        require(results['valid_totp_login'], 'valid_totp_login')
        results['valid_totp_exchanges_token'] = bool(exchange(fresh, private, response['data'], verifier).get('id_token'))
        fresh = Api()
        response, verifier, query = login(fresh, private, username, password)
        require(response.get('data') == 'NextMfa', 'recovery_challenge')
        route = '/api/login?' + urllib.parse.urlencode(query)
        response = fresh.request(route, {**common_login, 'recoveryCode': recovery})
        results['recovery_code_login'] = code_ok(response)
        if code_ok(response):
            exchange(fresh, private, response['data'], verifier)
        fresh = Api()
        response, _, query = login(fresh, private, username, password)
        require(response.get('data') == 'NextMfa', 'reused_recovery_challenge')
        results['recovery_code_single_use'] = not code_ok(fresh.request('/api/login?' + urllib.parse.urlencode(query),
            {**common_login, 'recoveryCode': recovery}))
        # Self-service can disable optional MFA; do not enroll the production owner.
        api.ok('/api/delete-mfa', user, form=True)
        response, _, _ = login(Api(), private, username, password)
        results['optional_mfa_can_be_disabled'] = code_ok(response)
        login_file = dict(x.split(': ', 1) for x in Path('/etc/headplane/admin-login.txt').read_text().splitlines() if ': ' in x)
        owner = Api()
        response, verifier, _ = login(owner, private, login_file['Username'], login_file['Password'])
        require(code_ok(response), 'existing_owner_password')
        owner_tokens = exchange(owner, private, response['data'], verifier)
        token = owner_tokens.get('id_token', '')
        require(bool(token), 'owner_token')
        claims = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '==='))
        require(claims.get('iss') == ORIGIN + '/auth' and bool(claims.get('sub')), 'owner_issuer_and_subject')
        private['owner_subject'] = claims['sub']
        Path('/etc/casdoor/credentials.json').write_text(json.dumps(private))
        results['existing_owner_password_and_stable_subject'] = True
        # End private provider sessions without outputting tokens or codes.
        for client in [api, owner]:
            client.request('/api/logout')
        for key, value in results.items():
            require(value is True, key)
        out = Path('/root/headplane-optional-20261113/provider-acceptance.json')
        out.write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(results, indent=2))
    finally:
        admin.ok('/api/delete-user', user)


if __name__ == '__main__':
    main()
