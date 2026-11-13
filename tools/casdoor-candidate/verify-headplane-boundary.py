"""Exercise an exclusively staged loopback candidate; never change live configuration."""
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import time

from checks import disabled_login_response, logged_out_response, protected_response, require

STAGE = Path('/root/headplane-mfa-20261113/app-candidate')
NAME = 'headplane-mfa-boundary-candidate'


def request(path, body=None, content_type='application/x-www-form-urlencoded', cookie=''):
    connection = http.client.HTTPConnection('127.0.0.1', 3002, timeout=10)
    try:
        connection.request('GET' if body is None else 'POST', path, body, {
            'Host': '140.143.127.180', 'Origin': 'https://140.143.127.180',
            'X-Forwarded-Proto': 'https', 'Content-Type': content_type, 'Cookie': cookie,
            'Remote-User': 'admin', 'Remote-Email': 'admin@headplane.local',
            'Authorization': 'Basic ZHVtbXk6ZHVtbXk=',
        })
        response = connection.getresponse()
        return response.status, response.getheaders(), response.read().decode()
    finally:
        connection.close()


def prepare(env):
    # Exclusive staging, fresh signing secret and no copied live sessions.
    STAGE.mkdir(mode=0o700)
    uid, gid = int(env['HEADPLANE_UID']), int(env['HEADPLANE_GID'])
    data = STAGE / 'data'
    data.mkdir(mode=0o700)
    os.chown(data, uid, gid)
    with sqlite3.connect('file:/var/lib/headplane/hp_persist.db?mode=ro', uri=True) as source:
        with sqlite3.connect(data / 'hp_persist.db') as target:
            source.backup(target)
            target.execute('DELETE FROM auth_sessions')
            require(target.execute('pragma integrity_check').fetchone()[0] == 'ok', 'Invalid database copy')
    os.chown(data / 'hp_persist.db', uid, gid)
    os.chmod(data / 'hp_persist.db', 0o600)
    # Explicit keys: no inherited bind address, proxy settings or signing secret.
    config = f'''server:
  host: 127.0.0.1
  port: 3002
  base_url: https://140.143.127.180
  cookie_secret: {secrets.token_hex(16)}
  cookie_secure: true
  cookie_max_age: 28800
  data_path: /var/lib/headplane
  proxy_auth:
    enabled: false
headscale:
  url: http://127.0.0.1:8081
  public_url: https://140.143.127.180
  config_path: /etc/headscale/config.yaml
  api_key_path: /etc/headplane/headscale-api-key
oidc:
  issuer: https://140.143.127.180/auth
  client_id: candidate-only
  client_secret: candidate-only-not-a-real-credential
  disable_api_key_login: true
  use_end_session: true
integration:
  agent:
    enabled: false
  docker:
    enabled: false
  kubernetes:
    enabled: false
    pod_name: headscale
  proc:
    enabled: false
'''
    path = STAGE / 'config.yaml'
    path.write_text(config)
    os.chown(path, 0, gid)
    os.chmod(path, 0o640)
    return path, data


def main():
    os.umask(0o077)
    require(not STAGE.exists(), 'Candidate staging already exists; refuse reuse')
    require(STAGE.parent.resolve() == Path('/root/headplane-mfa-20261113'), 'Unexpected candidate parent')
    env = dict(line.split('=', 1) for line in Path('/etc/headplane/runtime.env').read_text().splitlines() if '=' in line)
    container = None
    try:
        path, data = prepare(env)
        command = ['docker', 'create', '--name', NAME, '--init', '--network', 'host',
            '--user', f"{env['HEADPLANE_UID']}:{env['HEADPLANE_GID']}", '--group-add', env['HEADSCALE_GID'],
            '--read-only', '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '128', '--memory', '512m',
            '--log-opt', 'max-size=5m', '--log-opt', 'max-file=2', '-e', 'HEADPLANE_CONFIG_PATH=/candidate-config.yaml',
            '--mount', 'type=bind,src=/etc/headplane,dst=/etc/headplane,readonly',
            '--mount', 'type=bind,src=/etc/headscale,dst=/etc/headscale,readonly',
            '--mount', f'type=bind,src={path},dst=/candidate-config.yaml,readonly',
            '--mount', f'type=bind,src={data},dst=/var/lib/headplane',
            'headplane-local:0.8.2-mfa-prepared-20261113']
        container = subprocess.check_output(command, text=True).strip()
        subprocess.run(['docker', 'start', container], check=True, stdout=subprocess.DEVNULL)
        ready = False
        for _ in range(40):
            try:
                request('/admin/login?s=logout'); ready = True; break
            except OSError:
                time.sleep(0.25)
        require(ready, 'Candidate did not become ready')
        sockets = subprocess.check_output(['ss', '-H', '-lnt', 'sport = :3002'], text=True)
        require('127.0.0.1:3002' in sockets and '0.0.0.0:3002' not in sockets and '*:3002' not in sockets,
                'Candidate listener is not loopback-only')
        results = {'loopback_listener': True}
        for path in ['/admin/login', '/admin/login.data']:
            for body, kind in [('api_key=irrelevant', 'application/x-www-form-urlencoded'),
                               ('invalid multipart', 'multipart/form-data')]:
                status, headers, _ = request(path, body, kind)
                disabled_login_response(status, headers)
            results[path + ' disabled POSTs'] = True
        for cookie, language in [('', 'zh-CN'), ('hp_language=ImVuIg%3D%3D', 'en')]:
            status, _, body = request('/admin/login?s=logout', cookie=cookie)
            logged_out_response(status, body, language)
        results['bilingual_logged_out_pages'] = True
        status, headers, _ = request('/admin/machines')
        location = next((value for name, value in headers if name.lower() == 'location'), None)
        protected_response(status, location)
        results['basic_and_spoofed_principal_denied'] = True
        (STAGE.parent / 'app-boundary-acceptance.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(results, indent=2))
    finally:
        if container:
            subprocess.run(['docker', 'rm', '-f', container], check=True, stdout=subprocess.DEVNULL)
        if STAGE.exists():
            require(STAGE.resolve() == Path('/root/headplane-mfa-20261113/app-candidate'), 'Unsafe cleanup target')
            shutil.rmtree(STAGE)


if __name__ == '__main__':
    main()
