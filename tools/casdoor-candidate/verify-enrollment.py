"""Check actual official candidate behavior without printing test credentials."""
import base64
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import secrets
import struct
import time
import urllib.parse

spec = importlib.util.spec_from_file_location('candidate', Path(__file__).with_name('prepare.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Api, ROOT = module.Api, module.ROOT


def totp(secret):
    raw = base64.b32decode(secret + '=' * ((8 - len(secret) % 8) % 8))
    digest = hmac.new(raw, struct.pack('>Q', int(time.time()) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return f'{(struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000:06d}'


def main():
    private = json.loads((ROOT / 'credentials.json').read_text())
    admin = Api()
    admin.ok('/api/login', {'type':'login','signinMethod':'Password','organization':'built-in',
        'application':'app-built-in','username':'admin','password':private['maintenance_password']})
    username = 'enrollment-' + secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    owner = {'owner':'headplane','name':username}
    admin.ok('/api/add-user', {**owner,'password':password,'displayName':'Disposable enrollment check',
        'type':'normal-user','isAdmin':False,'signupApplication':'headplane'})
    result = {}
    try:
        user = Api()
        response = user.request('/api/login', {'type':'code','signinMethod':'Password','organization':'headplane',
            'application':'headplane','username':username,'password':password,
            'clientId':private['client_id'],'redirectUri':'https://140.143.127.180/admin/oidc/callback'})
        result['password_only_requires_enrollment'] = response.get('data') == 'RequiredMfa'
        common = {**owner,'mfaType':'app'}
        response = user.request('/api/mfa/setup/initiate', common, form=True)
        assert response['status'] == 'ok', 'Test setup: initiate was rejected'
        props = response['data']
        response = user.request('/api/mfa/setup/verify', {**common,'secret':props['secret'],'passcode':'invalid'},form=True)
        result['invalid_setup_code_rejected'] = response['status'] != 'ok'
        # Do not call successful verification before attempting enable.
        response = user.request('/api/mfa/setup/enable', {**common,'secret':props['secret'],
            'recoveryCodes':props['recoveryCodes'][0]},form=True)
        result['unverified_enable_rejected'] = response['status'] != 'ok'
        verifier = secrets.token_urlsafe(48)
        query = urllib.parse.urlencode({'clientId': private['client_id'],
            'redirectUri':'https://140.143.127.180/admin/oidc/callback',
            'scope':'openid email profile', 'state':secrets.token_urlsafe(16),
            'nonce':secrets.token_urlsafe(16), 'code_challenge_method':'S256',
            'code_challenge':base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')})
        response = user.request('/api/login?'+query, {'type':'code', 'application':'headplane',
            'organization':'headplane'})
        result['code_issuance_blocked_after_unverified_enable'] = not (
            response.get('status') == 'ok' and isinstance(response.get('data'), str)
            and response['data'] not in ['RequiredMfa','NextMfa']
        )
        if not result['code_issuance_blocked_after_unverified_enable']:
            tokens = user.request('/api/login/oauth/access_token', {'grant_type':'authorization_code',
                'client_id':private['client_id'], 'client_secret':private['client_secret'],
                'code':response['data'], 'code_verifier':verifier,
                'redirect_uri':'https://140.143.127.180/admin/oidc/callback'},form=True)
            result['id_token_denied_after_unverified_enable'] = not bool(tokens.get('id_token'))
        check = admin.ok('/api/get-user?id=headplane%2F'+username)
        result['ordinary_test_user_is_not_admin'] = check.get('isAdmin') is False
        Path('/root/headplane-mfa-20261113/enrollment-acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:
        admin.ok('/api/delete-user', owner)
    assert all(result.values()), 'Candidate failed mandatory enrollment acceptance; production cutover forbidden'


if __name__ == '__main__':
    main()
