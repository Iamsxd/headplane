#!/usr/bin/env python3
"""Provision the pinned dashboard and private credentials on the authorized server."""
import grp
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
import time
import urllib.request

IMAGE = 'ghcr.io/tale/headplane@sha256:b053a0a6699d0a67be3f0d9bae8e7dbe35ed67ae8448412adcbad7ea49866faa'


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    os.umask(0o077)
    stage = Path('/root/headplane-setup-20261113')
    baseline = stage / 'before'
    if not baseline.exists():
        baseline.mkdir(mode=0o700)
        shutil.copytree('/etc/nginx', baseline / 'nginx', symlinks=True)
        shutil.copytree('/etc/headscale', baseline / 'headscale', symlinks=True)
        nodes = subprocess.check_output(['runuser', '-u', 'headscale', '--', 'headscale',
                                         'nodes', 'list', '-o', 'json'])
        (baseline / 'nodes.json').write_bytes(nodes)
    try:
        account = pwd.getpwnam('headplane')
    except KeyError:
        subprocess.run(['useradd', '--system', '--user-group', '--home-dir', '/var/lib/headplane',
                        '--shell', '/usr/sbin/nologin', 'headplane'], check=True)
        account = pwd.getpwnam('headplane')
    configdir = Path('/etc/headplane')
    configdir.mkdir(mode=0o711, exist_ok=True)
    configdir.chmod(0o711)
    datadir = Path('/var/lib/headplane')
    datadir.mkdir(mode=0o700, exist_ok=True)
    os.chown(datadir, account.pw_uid, account.pw_gid)

    def secret_file(name, content, group=account.pw_gid, mode=0o640):
        path = configdir / name
        path.write_text(content)
        os.chown(path, 0, group)
        path.chmod(mode)

    secret_file('config.yaml', (stage / 'config.yaml').read_text())
    if not (configdir / 'cookie-secret').exists():
        secret_file('cookie-secret', secrets.token_hex(16))
    if not (configdir / 'headscale-api-key').exists():
        before = {int(item['id']) for item in json.loads(subprocess.check_output(
            ['runuser', '-u', 'headscale', '--', 'headscale', 'apikeys', 'list', '-o', 'json'])) or []}
        output = subprocess.run(['runuser', '-u', 'headscale', '--', 'headscale', 'apikeys',
                                 'create', '--expiration', '90d'], capture_output=True, text=True, check=True)
        key = output.stdout.strip()
        if len(key) < 20 or any(c.isspace() for c in key):
            raise RuntimeError('Unexpected API key format; refusing to write it')
        after = {int(item['id']) for item in json.loads(subprocess.check_output(
            ['runuser', '-u', 'headscale', '--', 'headscale', 'apikeys', 'list', '-o', 'json'])) or []}
        created = after-before
        if len(created) != 1:
            raise RuntimeError('Cannot uniquely identify the new dashboard API key')
        secret_file('headscale-api-key', key)
        secret_file('api-key-id', str(created.pop()))
    if not (configdir / 'admin.htpasswd').exists():
        password = secrets.token_urlsafe(18)
        hashed = subprocess.run(['htpasswd', '-niB', 'admin'], input=password+'\n',
                                capture_output=True, text=True, check=True).stdout
        secret_file('admin.htpasswd', hashed, group=grp.getgrnam('www-data').gr_gid)
        secret_file('admin-login.txt', 'Headplane management\nURL: https://140.143.127.180/admin/\n'
                    'Username: admin\nPassword: '+password+'\n', group=0, mode=0o600)
    secret_file('runtime.env', f'HEADPLANE_UID={account.pw_uid}\nHEADPLANE_GID={account.pw_gid}\n'
                f'HEADSCALE_GID={grp.getgrnam("headscale").gr_gid}\nHEADPLANE_IMAGE={IMAGE}\n',
                group=0, mode=0o600)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'headplane.service'], check=True)
    request = urllib.request.Request('http://127.0.0.1:3000/admin/', headers={
        'Remote-User': 'admin', 'Remote-Email': 'admin@headplane.local', 'Remote-Name': 'Administrator'})
    for attempt in range(90):
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                if response.status == 200:
                    print('Dashboard application ready; administrator identity initialized')
                    break
        except OSError:
            pass
        time.sleep(1)
    else:
        raise RuntimeError('Dashboard did not become healthy; inspect journalctl -u headplane')
    snippet = Path('/etc/nginx/snippets/headplane.conf')
    shutil.copyfile(stage / 'nginx-headplane.conf', snippet)
    snippet.chmod(0o644)
    changed = []
    for name in ['headscale-ip', 'headscale-public']:
        path = Path('/etc/nginx/sites-available') / name
        original = path.read_bytes()
        include = b'    include /etc/nginx/snippets/headplane.conf;\n'
        if include not in original:
            marker = b'    server_tokens off;\n'
            if original.count(marker) != 1:
                raise RuntimeError(f'Unexpected Nginx layout: {name}')
            changed.append((path, original))
            path.write_bytes(original.replace(marker, marker + include))
    try:
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    except Exception:
        for path, original in changed:
            path.write_bytes(original)
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        raise
    print('Headplane0.8.2 installed behind existing IP/domain HTTPS at /admin/')
    print('Login credentials retained privately; no API keys or passwords printed')


if __name__ == '__main__':
    main()
