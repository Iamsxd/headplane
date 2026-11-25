#!/usr/bin/env python3
"""Move the Tencent control and dashboard URLs together, with a scoped rollback."""
import argparse
from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

IP = 'https://140.143.127.180'
DOMAIN = 'https://hs.lovecanl.cn'
CONTROL = Path('/etc/headscale/config.yaml')
PROVIDER_DB = Path('/var/lib/casdoor/casdoor.db')
HEADPLANE = Path('/etc/headplane/config.yaml')
LOGIN_NOTE = Path('/etc/headplane/admin-login.txt')
CASDOOR = Path('/etc/casdoor/app.conf')
NGINX_DOMAIN = Path('/etc/nginx/sites-available/headscale-public')
NGINX_IP = Path('/etc/nginx/sites-available/headscale-ip')
CONFIGS = (HEADPLANE, LOGIN_NOTE, CASDOOR, NGINX_DOMAIN, NGINX_IP)
HEADPLANE_INCLUDE = '    include /etc/nginx/snippets/headplane.conf;\n'
CASDOOR_INCLUDE = '    include /etc/nginx/snippets/casdoor-proxy.conf;\n'
IP_REDIRECTS = '''    location = /admin { return 302 https://hs.lovecanl.cn/admin/; }
    location ^~ /admin/ {
        access_log off;
        return 302 https://hs.lovecanl.cn/admin/;
    }
    location = /auth { return 302 https://hs.lovecanl.cn/auth/account; }
    location ^~ /auth/ {
        access_log off;
        return 302 https://hs.lovecanl.cn/auth/account;
    }
'''


def run(*args):
    subprocess.run(args, check=True, timeout=120)


def replace_one(text, before, after):
    if text.count(before) != 1:
        raise RuntimeError('Migration matched an unexpected configuration layout')
    return text.replace(before, after)


def render():
    headplane = HEADPLANE.read_text()
    for key, suffix in [('base_url', ''), ('public_url', ''), ('issuer', '/auth'),
                        ('post_logout_redirect_uri', '/admin/login?s=logout')]:
        headplane = replace_one(headplane, f'  {key}: {IP}{suffix}\n', f'  {key}: {DOMAIN}{suffix}\n')
    login_note = replace_one(LOGIN_NOTE.read_text(), f'URL: {IP}/admin/\n', f'URL: {DOMAIN}/admin/\n')
    casdoor = CASDOOR.read_text()
    for key in ('origin', 'originFrontend'):
        casdoor = replace_one(casdoor, f'{key} = {IP}/auth\n', f'{key} = {DOMAIN}/auth\n')
    nginx_domain = replace_one(NGINX_DOMAIN.read_text(), HEADPLANE_INCLUDE, HEADPLANE_INCLUDE + CASDOOR_INCLUDE)
    nginx_ip = replace_one(NGINX_IP.read_text(), HEADPLANE_INCLUDE + CASDOOR_INCLUDE, IP_REDIRECTS)
    return dict(zip(CONFIGS, (headplane, login_note, casdoor, nginx_domain, nginx_ip), strict=True))


def provider_urls(before, after):
    """Update only the dashboard application's URL columns and its org link."""
    with closing(sqlite3.connect(f'file:{PROVIDER_DB}?mode=rw', uri=True)) as db:
        with db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT homepage_url, redirect_uris FROM application WHERE owner=? AND name=?',
                             ('admin', 'headplane')).fetchone()
            org = db.execute('SELECT website_url FROM organization WHERE owner=? AND name=?',
                             ('admin', 'headplane')).fetchone()
            paths = ['/admin/oidc/callback', '/admin/login?s=logout']
            expected = {before + path for path in paths}
            target = {after + path for path in paths}
            if row and row[0] == after + '/admin/' and set(json.loads(row[1])) == target and org == (after + '/admin/',):
                return  # Rollback may run before the migration transaction committed.
            if not row or row[0] != before + '/admin/' or set(json.loads(row[1])) != expected or org != (before + '/admin/',):
                raise RuntimeError('Unexpected Casdoor URLs. No provider rows changed.')
            db.execute('UPDATE application SET homepage_url=?,redirect_uris=? WHERE owner=? AND name=?',
                       (after + '/admin/', json.dumps([after + path for path in paths]), 'admin', 'headplane'))
            db.execute('UPDATE organization SET website_url=? WHERE owner=? AND name=?',
                       (after + '/admin/', 'admin', 'headplane'))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def wait_for_dashboard(origin):
    opener = urllib.request.build_opener(NoRedirect())
    until = time.monotonic() + 28
    while time.monotonic() < until:
        try:
            with opener.open(origin + '/auth/.well-known/openid-configuration', timeout=3) as response:
                discovery = json.load(response)
            if discovery.get('issuer') != origin + '/auth':
                raise ValueError('wrong issuer')
            try:
                opener.open(origin + '/admin/oidc/start', timeout=3).close()
            except urllib.error.HTTPError as response:
                with response:
                    location = urllib.parse.urlsplit(response.headers.get('Location', ''))
                    query = urllib.parse.parse_qs(location.query)
                    if (response.code == 302 and location.geturl().startswith(origin + '/auth/') and
                        query.get('redirect_uri') == [origin + '/admin/oidc/callback'] and
                        query.get('code_challenge_method') == ['S256']):
                        return
        except (OSError, ValueError):
            pass
        time.sleep(0.75)
    raise RuntimeError('Dashboard did not advertise the selected HTTPS issuer and callback')


def start_dashboard(origin):
    run('nginx', '-t')
    run('systemctl', 'reload', 'nginx')
    run('systemctl', 'start', 'casdoor', 'headplane')
    wait_for_dashboard(origin)


def backup_path(stage, config):
    return stage / f'{config.parent.name}-{config.name}.before'


def rollback(stage, atomic_write):
    originals = {path: backup_path(stage, path).read_bytes() for path in CONFIGS}
    run('systemctl', 'stop', 'headplane', 'casdoor')
    try:
        provider_urls(DOMAIN, IP)
    finally:
        for path, content in originals.items():
            atomic_write(path, content, path.stat())
        if f'server_url: {DOMAIN}\n' in CONTROL.read_text():
            run('/usr/local/sbin/headscale-endpoint', 'ip')
        start_dashboard(IP)
    print('Restored IP control and dashboard URLs. Data and identity files were retained.', flush=True)


def switch(stage, atomic_write):
    if CONTROL.read_text().splitlines().count(f'server_url: {IP}') != 1:
        raise RuntimeError('Expected the IP control endpoint before switching')
    candidate = render()
    run('/usr/local/sbin/headscale-backup.py')
    for path in (*CONFIGS, CONTROL):
        with backup_path(stage, path).open('xb') as receipt:
            receipt.write(path.read_bytes())
    try:
        run('systemctl', 'stop', 'headplane', 'casdoor')
        provider_urls(IP, DOMAIN)
        for path, text in candidate.items():
            atomic_write(path, text.encode(), path.stat())
        start_dashboard(DOMAIN)
        run('/usr/local/sbin/headscale-endpoint', 'domain')
    except Exception:
        rollback(stage, atomic_write)
        raise
    print('Domain control and dashboard configured and healthy. IP control proxy retained.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('apply', 'rollback'))
    parser.add_argument('stage', type=Path, help='Existing root-only migration directory')
    args = parser.parse_args()
    os.umask(0o077)
    stage_stat = args.stage.stat()
    if os.geteuid() != 0 or not args.stage.is_dir() or stage_stat.st_uid != 0 or stage_stat.st_mode & 0o077:
        parser.error('Run as root and use a private root-owned migration directory')
    atomic_write = runpy.run_path('/usr/local/sbin/headscale-endpoint')['atomic_write']
    with open('/run/lock/headscale-domain-migration.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == 'apply':
            switch(args.stage, atomic_write)
        else:
            rollback(args.stage, atomic_write)


if __name__ == '__main__':
    main()
