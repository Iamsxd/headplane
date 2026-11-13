#!/usr/bin/env python3
"""Rotate the dashboard's private90-day API key without changing its login password."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import urllib.request


def replace_private(path, content):
    metadata = path.stat()
    descriptor, temporary = tempfile.mkstemp(prefix='.rotate-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            if hasattr(os, 'fchown'):
                os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            os.chmod(temporary, stat.S_IMODE(metadata.st_mode))
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def rotate_key(keyfile, idfile, create, restart, ready, revoke):
    old_key, old_id = keyfile.read_text(), idfile.read_text().strip()
    new_key, new_id = create()
    try:
        replace_private(keyfile, new_key)
        replace_private(idfile, new_id)
        restart()
        ready()
    except Exception:
        replace_private(keyfile, old_key)
        replace_private(idfile, old_id)
        try:
            restart()
        finally:
            revoke(new_id)
        raise
    revoke(old_id)


def main():
    import fcntl
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    os.umask(0o077)
    keyfile = Path('/etc/headplane/headscale-api-key')
    idfile = Path('/etc/headplane/api-key-id')

    def hs(*arguments):
        return subprocess.run(['runuser', '-u', 'headscale', '--', 'headscale', *arguments],
                              check=True, capture_output=True, text=True).stdout.strip()

    def create():
        before = {int(k['id']) for k in json.loads(hs('apikeys', 'list', '-o', 'json')) or []}
        token = hs('apikeys', 'create', '--expiration', '90d')
        if len(token) < 20 or any(c.isspace() for c in token):
            raise RuntimeError('Unexpected API key format')
        after = {int(k['id']) for k in json.loads(hs('apikeys', 'list', '-o', 'json')) or []}
        created = after - before
        if len(created) != 1:
            raise RuntimeError('Cannot uniquely identify newly created API key')
        return token, str(created.pop())

    def ready():
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            try:
                token = keyfile.read_text().strip()
                request = urllib.request.Request('http://127.0.0.1:8081/api/v1/node',
                                                  headers={'Authorization': 'Bearer '+token})
                with urllib.request.urlopen(request, timeout=3) as response:
                    if response.status != 200:
                        raise OSError('Headscale API not ready')
                request = urllib.request.Request('http://127.0.0.1:3000/admin/machines',
                                                  headers={'Remote-User': 'admin',
                                                           'Remote-Email': 'admin@headplane.local'})
                with urllib.request.urlopen(request, timeout=3) as response:
                    if response.status == 200:
                        return
            except OSError:
                pass
            time.sleep(0.5)
        raise RuntimeError('Dashboard API or application failed readiness after credential rotation')

    with open('/run/lock/headplane-key-rotate.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rotate_key(keyfile, idfile, create,
                   lambda: subprocess.run(['systemctl', 'restart', 'headplane.service'], check=True),
                   ready, lambda identifier: hs('apikeys', 'expire', '--id', identifier))
    print('Dashboard API key rotated; previous key expired; administrator password unchanged')


if __name__ == '__main__':
    main()
