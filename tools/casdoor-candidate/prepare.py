"""Private disposable upstream interoperability test; never prints credentials."""
import copy
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.parse
import urllib.request

ROOT = Path('/root/headplane-mfa-20261113/casdoor-candidate')
BASE = 'http://127.0.0.1:18000/auth'
ORIGIN = 'https://140.143.127.180/auth'
IMAGE = 'sha256:3af7268ddfcfac032bfff4fc67acaea284278269c6caf5bc761609ac25a6596b'


class Api:
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, route, payload=None, form=False):
        body = None if payload is None else (urllib.parse.urlencode(payload).encode() if form else json.dumps(payload).encode())
        req = urllib.request.Request(BASE + route, data=body, headers={
            'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json',
            'Origin': 'https://140.143.127.180', 'X-Forwarded-Proto': 'https',
            'Host': '140.143.127.180', 'Accept-Language': 'en',
        })
        with self.client.open(req, timeout=20) as resp:
            return json.load(resp)

    def ok(self, route, payload=None):
        result = self.request(route, payload)
        if result.get('status') != 'ok':
            raise RuntimeError(route + ': ' + str(result.get('msg')))
        return result.get('data')


def main():
    os.umask(0o077)
    ROOT.mkdir(mode=0o700)
    for name in ['conf', 'data', 'sessions']:
        p = ROOT / name
        p.mkdir(mode=0o700)
        os.chown(p, 1000, 1000)
    private = {'maintenance_password': secrets.token_urlsafe(36), 'test_password': secrets.token_urlsafe(24),
               'client_id': 'headplane-' + secrets.token_hex(12), 'client_secret': secrets.token_urlsafe(36)}
    (ROOT / 'credentials.json').write_text(json.dumps(private))
    config = (ROOT.parent / 'casdoor-default.conf').read_text()
    values = {
        'httpport': '8000', 'runmode': 'prod', 'driverName': 'sqlite3',
        'dataSourceName': 'file:/var/lib/casdoor/casdoor.db?cache=shared&_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)',
        'dbName': 'casdoor', 'socks5Proxy': '', 'origin': ORIGIN, 'originFrontend': ORIGIN,
        'basePath': '/auth', 'defaultLanguage': 'zh', 'defaultApplication': 'headplane',
        'initAdminPassword': private['maintenance_password'], 'initDataFile': '', 'isDemoMode': 'false',
        'ldapServerPort': '0', 'ldapsServerPort': '0', 'radiusServerPort': '0',
        'logConfig': '{"adapter":"console","level":4}', 'sessionCookieLifeTime': '28800',
    }
    lines = []
    seen = set()
    for line in config.splitlines():
        name = line.split('=', 1)[0].strip()
        if name in values:
            lines.append(name + ' = ' + values[name]); seen.add(name)
        else:
            lines.append(line)
    lines += [k + ' = ' + v for k, v in values.items() if k not in seen]
    p = ROOT / 'conf/app.conf'; p.write_text('\n'.join(lines) + '\n'); os.chown(p, 1000, 1000)
    subprocess.run(['docker', 'run', '-d', '--name', 'casdoor-mfa-candidate', '--read-only',
        '--user', '1000:1000', '--cap-drop=ALL', '--security-opt=no-new-privileges:true',
        '--memory=512m', '--memory-swap=512m', '--pids-limit=128',
        '--log-opt=max-size=5m', '--log-opt=max-file=2', '-p', '127.0.0.1:18000:8000',
        '-v', str(p)+':/conf/app.conf:ro', '-v', str(ROOT/'data')+':/var/lib/casdoor',
        '-v', str(ROOT/'sessions')+':/tmp', '--tmpfs', '/logs:uid=1000,gid=1000,mode=700,size=16m',
        '--tmpfs', '/files:uid=1000,gid=1000,mode=700,size=8m', IMAGE], check=True, stdout=subprocess.DEVNULL)
    api = Api()
    for _ in range(40):
        try:
            r = api.request('/api/health')
            break
        except Exception:
            time.sleep(0.5)
    else:
        raise RuntimeError('candidate health did not become ready')
    api.ok('/api/login', {'type':'login', 'signinMethod':'Password', 'organization':'built-in',
        'application':'app-built-in', 'username':'admin', 'password':private['maintenance_password'], 'autoSignin':False})
    org = api.ok('/api/get-organization?id=admin%2Fbuilt-in')
    org.update(name='headplane', displayName='Headplane', websiteUrl='https://140.143.127.180/admin/',
               languages=['zh','en'], mfaItems=[{'name':'app','rule':'Required'}], mfaRememberInHours=0,
               enableTour=False, dcrPolicy='disabled', defaultTokenFormat='JWT-Standard',
               masterPassword='', defaultPassword='')
    api.ok('/api/add-organization', org)
    app = api.ok('/api/get-application?id=admin%2Fapp-built-in')
    app.update(name='headplane', displayName='Headplane', organization='headplane',
        clientId=private['client_id'], clientSecret=private['client_secret'],
        redirectUris=['https://140.143.127.180/admin/oidc/callback', 'https://140.143.127.180/admin/login?s=logout'],
        tokenFormat='JWT-Standard', tokenSigningMethod='RS256', expireInHours=8, cookieExpireInHours=8,
        grantTypes=['authorization_code'], enableSignUp=False, disableSelfSignup=True,
        enableGuestSignin=False, enableCodeSignin=False, enableAutoSignin=False,
        enableWebAuthn=False, enableSigninSession=True, providers=[],
        signinMethods=[{'name':'Password','displayName':'Password','rule':'All'}],
        failedSigninLimit=5, failedSigninFrozenTime=10)
    app.pop('organizationObj', None)
    api.ok('/api/add-application', app)
    api.ok('/api/add-user', {'owner':'headplane', 'name':'mfa-test', 'displayName':'Disposable MFA test',
        'password':private['test_password'], 'type':'normal-user', 'language':'zh',
        'isAdmin':False, 'signupApplication':'headplane', 'email':'test@headplane.local'})
    print('Private official SQLite candidate initialized; no public routes changed.')


if __name__ == '__main__':
    main()
