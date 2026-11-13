#!/usr/bin/env python3
"""Exercise real TLS/OIDC/session logout using a private copied dashboard database."""
import http.client
import http.cookiejar
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).parent
cfg = SourceFileLoader('oidc_config', str(HERE / 'headplane-oidc-config.py')).load_module()
ORIGIN = cfg.ORIGIN
ROOT = Path('/root/headplane-optional-20261113/oidc-candidate')


def require(condition, name):
    if not condition:
        raise RuntimeError('Acceptance failed: ' + name)


class LocalTLS(http.client.HTTPSConnection):
    def connect(self):
        self.sock = socket.create_connection(('127.0.0.1', 1443), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname='140.143.127.180')


class Handler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(LocalTLS, req, context=self._context)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Browser:
    def __init__(self, production=False):
        self.production = production
        self.cookies = http.cookiejar.CookieJar()
        handler = urllib.request.HTTPSHandler(context=ssl.create_default_context()) if production else Handler(context=ssl.create_default_context())
        self.client = urllib.request.build_opener(handler, urllib.request.HTTPCookieProcessor(self.cookies), NoRedirect())

    def request(self, path, payload=None, headers=None):
        if path.startswith('/'):
            path = ORIGIN + path
        body = None if payload is None else (json.dumps(payload).encode() if isinstance(payload, dict) else payload.encode())
        req = urllib.request.Request(path, body, headers={
            'Content-Type': 'application/json' if isinstance(payload, dict) else 'application/x-www-form-urlencoded',
            'Origin': ORIGIN, **(headers or {})})
        try:
            response = self.client.open(req, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read().decode()

    def api(self, path, payload=None):
        status, _, text = self.request(path, payload)
        require(status == 200, 'provider_api_http_status')
        return json.loads(text)


def sign_in(browser, username, password):
    status, headers, _ = browser.request('/admin/oidc/start')
    require(status == 302, 'oidc_start_status_' + str(status) + '_path_' + urllib.parse.urlsplit(headers.get('Location', '')).path)
    authorization = headers['Location']
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(authorization).query))
    camel = {'clientId': q['client_id'], 'redirectUri': q['redirect_uri'], 'responseType': 'code',
        'scope': q['scope'], 'state': q['state'], 'nonce': q['nonce'],
        'code_challenge': q['code_challenge'], 'code_challenge_method': q['code_challenge_method']}
    response = browser.api('/auth/api/login?' + urllib.parse.urlencode(camel), {'type': 'code',
        'application': 'headplane', 'organization': 'headplane', 'signinMethod': 'Password',
        'username': username, 'password': password})
    require(response.get('status') == 'ok' and response.get('data') not in ['', 'NextMfa', 'RequiredMfa', None], 'password_oidc_code')
    callback = q['redirect_uri'] + '?' + urllib.parse.urlencode({'code': response['data'], 'state': q['state']})
    return callback, q


def check_dashboard(browser, expected=None):
    results = {}
    login = dict(x.split(': ', 1) for x in Path('/etc/headplane/admin-login.txt').read_text().splitlines() if ': ' in x)
    callback, query = sign_in(browser, login['Username'], login['Password'])
    bad = callback.replace('state=' + query['state'], 'state=invalid')
    status, headers, _ = browser.request(bad)
    results['mismatched_state_rejected'] = status == 302 and 'error_auth_failed' in headers.get('Location', '')
    status, headers, _ = browser.request(callback)
    results['real_tls_oidc_callback'] = status == 302 and headers.get('Location', '').endswith('/admin/')
    require(results['real_tls_oidc_callback'], 'real_tls_oidc_callback')
    cookies = headers.get_all('Set-Cookie', [])
    results['secure_httponly_session_cookie'] = any('HttpOnly' in c and 'Secure' in c and 'SameSite=Lax' in c for c in cookies)
    saved = [(c.name, c.value, c.domain, c.path) for c in browser.cookies if c.path.startswith('/admin')]
    status, _, body = browser.request('/admin/machines')
    results['owner_dashboard'] = status == 200 and ('设备' in body or 'Machines' in body)
    require(results['owner_dashboard'], 'owner_dashboard')
    for cookie, label in [('', '设备'), ('hp_language=ImVuIg%3D%3D', 'Machines')]:
        headers = {'Cookie': '; '.join(c.name + '=' + c.value for c in browser.cookies) + ('; ' + cookie if cookie else '')}
        status, _, body = browser.request('/admin/machines', headers=headers)
        require(status == 200 and label in body, 'bilingual_authenticated_dashboard')
    results['bilingual_authenticated_dashboard'] = True
    status, headers, _ = browser.request(callback)
    results['reused_authorization_code_rejected'] = status == 302 and 'error_auth_failed' in headers.get('Location', '')
    anonymous = Browser(production=browser.production)
    for path in ['/admin/login', '/admin/login.data']:
        status, headers, _ = anonymous.request(path, 'api_key=invalid', headers={'Remote-User': 'admin', 'Remote-Email': 'admin@headplane.local'})
        blocked = status == 403 or (status == 302 and headers.get('Location', '').endswith('/admin/oidc/start'))
        require(blocked and not headers.get_all('Set-Cookie'), 'disabled_api_key_post_' + path + '_status_' + str(status) + '_sets_cookie_' + str(bool(headers.get_all('Set-Cookie'))))
    status, headers, _ = anonymous.request('/admin/machines')
    require(status == 302 and '/login' in headers.get('Location', ''), 'spoofed_identity_denied')
    results['disabled_api_key_posts'] = True
    status, headers, _ = browser.request('/admin/logout', '')
    require(status == 302 and '/auth/api/logout?' in headers.get('Location', ''), 'federated_logout_redirect')
    location = headers['Location']
    status, headers, _ = browser.request(location)
    require(status in [302, 303] and headers.get('Location', '').endswith('/admin/login?s=logout'), 'provider_logout_return')
    for _ in range(2):
        status, headers, body = browser.request('/admin/login?s=logout')
        require(status == 200 and ('你已退出登录' in body or 'logged out' in body.lower()), 'stable_logged_out_page')
    results['federated_logout_and_refresh'] = True
    fresh = Browser(production=getattr(browser, 'production', False))
    for name, value, domain, path in saved:
        fresh.cookies.set_cookie(http.cookiejar.Cookie(0, name, value, None, False, domain, False, False, path, True, True, None, True, None, None, {}))
    status, headers, _ = fresh.request('/admin/machines')
    results['copied_app_cookie_revoked'] = status == 302 and '/login' in headers.get('Location', '')
    account = browser.api('/auth/api/get-account')
    results['provider_sso_session_ended'] = account.get('status') != 'ok' or not account.get('data')
    for name, ok in results.items():
        require(ok is True, name)
    return results


def prepare():
    ROOT.mkdir(mode=0o700)
    env = dict(x.split('=', 1) for x in Path('/etc/headplane/runtime.env').read_text().splitlines() if '=' in x)
    uid, gid = int(env['HEADPLANE_UID']), int(env['HEADPLANE_GID'])
    private = json.loads(Path('/etc/casdoor/credentials.json').read_text())
    secret = Path('/etc/headplane/oidc-client-secret')
    secret.write_text(private['client_secret'])
    os.chown(secret, 0, gid); os.chmod(secret, 0o640)
    data = ROOT / 'data'; data.mkdir(mode=0o700); os.chown(data, uid, gid)
    with sqlite3.connect('file:/var/lib/headplane/hp_persist.db?mode=ro', uri=True) as source, sqlite3.connect(data / 'hp_persist.db') as target:
        source.backup(target)
        target.execute('DELETE FROM auth_sessions')
        rows = target.execute('SELECT id,role,caps,headscale_user_id FROM users WHERE sub=?', ('proxy:admin',)).fetchall()
        require(len(rows) == 1 and rows[0][1] == 'owner', 'single_expected_owner')
        target.execute('UPDATE users SET sub=? WHERE id=?', (private['owner_subject'], rows[0][0]))
    os.chown(data / 'hp_persist.db', uid, gid)
    path = ROOT / 'config.yaml'; path.write_text(cfg.render(private['client_id'], 3002, secrets.token_hex(16)))
    os.chown(path, 0, gid); os.chmod(path, 0o640)
    nginx = Path('/etc/nginx/conf.d/headplane-oidc-candidate.conf')
    nginx.write_text('''server {
    listen 127.0.0.1:1443 ssl;
    server_name 140.143.127.180;
    ssl_certificate /etc/letsencrypt-ip/live/headscale-ip/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt-ip/live/headscale-ip/privkey.pem;
    access_log off;
    include /etc/nginx/snippets/casdoor-proxy.conf;
    location /admin/ {
        proxy_pass http://127.0.0.1:3002;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Remote-User "";
        proxy_set_header Authorization "";
    }
}
''')
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    subprocess.run(['docker', 'run', '-d', '--name', 'headplane-oidc-candidate', '--init', '--network', 'host',
        '--user', f'{uid}:{gid}', '--group-add', env['HEADSCALE_GID'], '--read-only',
        '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--pids-limit', '128', '--memory', '512m', '--log-opt', 'max-size=5m', '--log-opt', 'max-file=2',
        '-e', 'HEADPLANE_CONFIG_PATH=/candidate-config.yaml',
        '-v', '/etc/headplane:/etc/headplane:ro', '-v', '/etc/headscale:/etc/headscale:ro',
        '-v', str(path) + ':/candidate-config.yaml:ro', '-v', str(data) + ':/var/lib/headplane', cfg.IMAGE], check=True, stdout=subprocess.DEVNULL)
    for _ in range(60):
        try:
            status, _, _ = Browser().request('/admin/login?s=logout')
            if status == 200:
                break
            time.sleep(0.5)
        except OSError:
            time.sleep(0.5)
    else:
        raise RuntimeError('Candidate unavailable')
    return rows[0]


def main():
    os.umask(0o077)
    try:
        before = prepare()
        results = check_dashboard(Browser())
        with sqlite3.connect(ROOT / 'data/hp_persist.db') as db:
            after = db.execute('SELECT id,role,caps,headscale_user_id FROM users WHERE role=?', ('owner',)).fetchall()
        require(after == [before], 'owner_identity_role_caps_link_preserved')
        results['owner_identity_role_caps_link_preserved'] = True
        (ROOT.parent / 'oidc-acceptance.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(results, indent=2))
    finally:
        with (ROOT.parent / 'oidc-candidate-private.log').open('w') as log:
            subprocess.run(['docker', 'logs', 'headplane-oidc-candidate'], stdout=log, stderr=subprocess.STDOUT)
        subprocess.run(['docker', 'rm', '-f', 'headplane-oidc-candidate'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Path('/etc/nginx/conf.d/headplane-oidc-candidate.conf').unlink(missing_ok=True)
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        if ROOT.exists():
            require(ROOT.resolve() == Path('/root/headplane-optional-20261113/oidc-candidate'), 'safe_candidate_cleanup')
            shutil.rmtree(ROOT)


if __name__ == '__main__':
    main()
