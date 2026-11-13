#!/usr/bin/env python3
"""Initialize the pinned official provider privately; never print credentials."""
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.parse
import urllib.request

ORIGIN = 'https://140.143.127.180'
BASE = 'http://127.0.0.1:18000/auth'
IMAGE = 'sha256:3af7268ddfcfac032bfff4fc67acaea284278269c6caf5bc761609ac25a6596b'
ETC = Path('/etc/casdoor')
DATA = Path('/var/lib/casdoor')


class Api:
    def __init__(self, base=BASE):
        self.base = base
        self.cookies = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, route, payload=None, form=False):
        body = None if payload is None else (urllib.parse.urlencode(payload).encode() if form else json.dumps(payload).encode())
        req = urllib.request.Request(self.base + route, data=body, headers={
            'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json',
            'Host': '140.143.127.180', 'Origin': ORIGIN, 'X-Forwarded-Proto': 'https',
            'X-Forwarded-For': '127.0.0.1', 'Accept-Language': 'en',
        })
        with self.client.open(req, timeout=20) as response:
            return json.load(response)

    def ok(self, route, payload=None, form=False):
        result = self.request(route, payload, form)
        if result.get('status') != 'ok':
            raise RuntimeError('Provider rejected ' + route.split('?')[0])
        return result.get('data')


def maintenance():
    private = json.loads((ETC / 'credentials.json').read_text())
    api = Api()
    api.ok('/api/login', {'type': 'login', 'signinMethod': 'Password', 'organization': 'built-in',
        'application': 'app-built-in', 'username': 'admin', 'password': private['maintenance_password']})
    return api, private


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    os.umask(0o077)
    if ETC.exists() or DATA.exists():
        raise SystemExit('Provider paths already exist; refusing to overwrite')
    ETC.mkdir(mode=0o700)
    DATA.mkdir(mode=0o700)
    os.chown(DATA, 1000, 1000)
    (DATA / 'sessions').mkdir(mode=0o700)
    os.chown(DATA / 'sessions', 1000, 1000)
    private = {'maintenance_password': secrets.token_urlsafe(36),
        'client_id': 'headplane-' + secrets.token_hex(12), 'client_secret': secrets.token_urlsafe(36)}
    (ETC / 'credentials.json').write_text(json.dumps(private))
    source = Path('/root/headplane-mfa-20261113/casdoor-default.conf').read_text()
    values = {'httpport': '8000', 'runmode': 'prod', 'driverName': 'sqlite3',
        'dataSourceName': 'file:/var/lib/casdoor/casdoor.db?cache=shared&_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)',
        'dbName': 'casdoor', 'socks5Proxy': '', 'origin': ORIGIN + '/auth', 'originFrontend': ORIGIN + '/auth',
        'basePath': '/auth', 'defaultLanguage': 'zh', 'defaultApplication': 'headplane',
        'initAdminPassword': private['maintenance_password'], 'initDataFile': '', 'isDemoMode': 'false',
        'ldapServerPort': '0', 'ldapsServerPort': '0', 'radiusServerPort': '0',
        'logConfig': '{"adapter":"console","level":4}', 'sessionCookieLifeTime': '28800',
        'trustedProxies': '127.0.0.1/32,172.17.0.0/16'}
    seen = set()
    lines = []
    for line in source.splitlines():
        name = line.split('=', 1)[0].strip()
        if name in values:
            lines.append(name + ' = ' + values[name]); seen.add(name)
        else:
            lines.append(line)
    lines += [k + ' = ' + v for k, v in values.items() if k not in seen]
    config = ETC / 'app.conf'
    config.write_text('\n'.join(lines) + '\n')
    os.chown(config, 1000, 1000)
    os.chmod(config, 0o600)
    (ETC / 'runtime.env').write_text('CASDOOR_IMAGE=' + IMAGE + '\n')
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'casdoor'], check=True)
    for _ in range(80):
        try:
            Api().request('/api/health'); break
        except Exception:
            time.sleep(0.5)
    else:
        raise RuntimeError('Provider did not become ready')
    api, private = maintenance()
    login = dict(line.split(': ', 1) for line in Path('/etc/headplane/admin-login.txt').read_text().splitlines() if ': ' in line)
    username, password = login['Username'], login['Password']
    org = api.ok('/api/get-organization?id=admin%2Fbuilt-in')
    org.update(name='headplane', displayName='Headplane', websiteUrl=ORIGIN + '/admin/',
        languages=['zh', 'en'], mfaItems=[{'name': 'app', 'rule': 'Optional'}], mfaRememberInHours=0,
        enableTour=False, defaultApplication='headplane', dcrPolicy='disabled', defaultTokenFormat='JWT-Standard',
        masterPassword='', defaultPassword='', ipWhitelist='')
    api.ok('/api/add-organization', org)
    app = api.ok('/api/get-application?id=admin%2Fapp-built-in')
    app.update(name='headplane', displayName='Headplane', organization='headplane',
        homepageUrl=ORIGIN + '/admin/', clientId=private['client_id'], clientSecret=private['client_secret'],
        redirectUris=[ORIGIN + '/admin/oidc/callback', ORIGIN + '/admin/login?s=logout'],
        tokenFormat='JWT-Standard', tokenSigningMethod='RS256', expireInHours=8, cookieExpireInHours=8,
        grantTypes=['authorization_code'], enableSignUp=False, disableSelfSignup=True,
        enableGuestSignin=False, enableCodeSignin=False, enableAutoSignin=False, enableWebAuthn=False,
        enableSigninSession=True, providers=[], ipWhitelist='',
        signinMethods=[{'name': 'Password', 'displayName': 'Password', 'rule': 'All'}],
        failedSigninLimit=5, failedSigninFrozenTime=10)
    app.pop('organizationObj', None)
    api.ok('/api/add-application', app)
    api.ok('/api/add-user', {'owner': 'headplane', 'name': username, 'displayName': 'Administrator',
        'password': password, 'email': 'admin@headplane.local', 'type': 'normal-user', 'language': 'zh',
        'isAdmin': False, 'signupApplication': 'headplane'})
    user = api.ok('/api/get-user?id=headplane%2F' + urllib.parse.quote(username, safe=''))
    private.update(owner_username=username, owner_provider_id=user['id'])
    (ETC / 'credentials.json').write_text(json.dumps(private))
    for kind, id_ in [('application', 'app-built-in'), ('organization', 'built-in'), ('user', 'admin')]:
        owner = 'built-in' if kind == 'user' else 'admin'
        q = urllib.parse.urlencode({'id': owner + '/' + id_})
        obj = api.ok('/api/get-' + kind + '?' + q)
        obj['ipWhitelist'] = '127.0.0.1/32,::1/128'
        obj.pop('organizationObj', None)
        api.ok('/api/update-' + kind + '?' + q, obj)
    # Startup password is needed only on first initialization, never expose it to the runtime afterward.
    config.write_text('\n'.join('initAdminPassword =' if x.startswith('initAdminPassword =') else x for x in lines) + '\n')
    subprocess.run(['systemctl', 'restart', 'casdoor'], check=True)
    print('Official Casdoor initialized with SQLite and optional TOTP; maintenance restricted to loopback.')


if __name__ == '__main__':
    main()
