#!/usr/bin/env python3
"""Create a private, consistent snapshot of Headscale data and identity keys."""
from datetime import datetime, timezone
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3


if os.geteuid() != 0:
    raise SystemExit('Run as root to back up Headscale identity keys.')
os.umask(0o077)
destination = Path('/var/backups/headscale') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
destination.mkdir(parents=True, mode=0o700)

with closing(sqlite3.connect('file:/var/lib/headscale/db.sqlite?mode=ro', uri=True)) as source:
    with closing(sqlite3.connect(destination / 'db.sqlite')) as target:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'

sources = {
    'config.yaml': '/etc/headscale/config.yaml',
    'policy.hujson': '/etc/headscale/policy.hujson',
    'noise_private.key': '/var/lib/headscale/noise_private.key',
    'derp_server_private.key': '/var/lib/headscale/derp_server_private.key',
    'nginx-preview.conf': '/etc/nginx/sites-available/headscale-preview',
}
production_sources = {
    'nginx-public.conf': '/etc/nginx/sites-available/headscale-public',
    'nginx-acme.conf': '/etc/nginx/sites-available/headscale-acme',
    'nginx-upgrade.conf': '/etc/nginx/conf.d/headscale-upgrade.conf',
    'tls-fullchain.pem': '/etc/letsencrypt/live/hs.lovecanl.cn/fullchain.pem',
    'tls-privkey.pem': '/etc/letsencrypt/live/hs.lovecanl.cn/privkey.pem',
    'certbot-renewal.conf': '/etc/letsencrypt/renewal/hs.lovecanl.cn.conf',
    'certbot-deploy-hook': '/etc/letsencrypt/renewal-hooks/deploy/20-reload-nginx',
}
if Path(production_sources['nginx-public.conf']).exists():
    sources.update(production_sources)
ip_sources = {
    'nginx-ip.conf': '/etc/nginx/sites-available/headscale-ip',
    'nginx-ip-acme.conf': '/etc/nginx/sites-available/headscale-ip-acme',
    'ip-tls-fullchain.pem': '/etc/letsencrypt-ip/live/headscale-ip/fullchain.pem',
    'ip-tls-privkey.pem': '/etc/letsencrypt-ip/live/headscale-ip/privkey.pem',
    'ip-certbot-renewal.conf': '/etc/letsencrypt-ip/renewal/headscale-ip.conf',
    'ip-certbot-deploy-hook': '/etc/letsencrypt-ip/renewal-hooks/deploy/20-reload-nginx',
    'ip-certbot-renew.service': '/etc/systemd/system/certbot-ip-renew.service',
    'ip-certbot-renew.timer': '/etc/systemd/system/certbot-ip-renew.timer',
    'headscale-endpoint': '/usr/local/sbin/headscale-endpoint',
}
if Path(ip_sources['nginx-ip.conf']).exists():
    sources.update(ip_sources)
headplane_sources = {
    'headplane-config.yaml': '/etc/headplane/config.yaml',
    'headplane-cookie-secret': '/etc/headplane/cookie-secret',
    'headplane-api-key': '/etc/headplane/headscale-api-key',
    'headplane-api-key-id': '/etc/headplane/api-key-id',
    'headplane-admin.htpasswd': '/etc/headplane/admin.htpasswd',
    'headplane-admin-login.txt': '/etc/headplane/admin-login.txt',
    'headplane-runtime.env': '/etc/headplane/runtime.env',
    'headplane.service': '/etc/systemd/system/headplane.service',
    'headplane-nginx.conf': '/etc/nginx/snippets/headplane.conf',
    'headplane-key-rotate.py': '/usr/local/sbin/headplane-key-rotate.py',
    'headplane-key-rotate.service': '/etc/systemd/system/headplane-key-rotate.service',
    'headplane-key-rotate.timer': '/etc/systemd/system/headplane-key-rotate.timer',
}
if Path(headplane_sources['headplane-config.yaml']).exists():
    sources.update(headplane_sources)
    with closing(sqlite3.connect('file:/var/lib/headplane/hp_persist.db?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(destination / 'headplane-persist.db')) as target:
            source.backup(target)
            assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
for name, path in sources.items():
    shutil.copyfile(path, destination / name)
manifest = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'sqlite_integrity_check': 'ok',
    'sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
               for path in destination.iterdir() if path.is_file()},
}
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print(f'Headscale backup complete: {destination}')
