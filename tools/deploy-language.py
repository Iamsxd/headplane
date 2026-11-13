#!/usr/bin/env python3
"""Switch only the Headplane image after backup, with readiness rollback."""
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

STAGE = Path('/root/headplane-language-20261113')


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def identities():
    nodes = json.loads(run('headscale', 'nodes', 'list', '-o', 'json'))
    return sorted((str(n['id']), n.get('given_name', n.get('givenName')), tuple(n.get('ip_addresses', n.get('ipAddresses', []))),
                   str((n.get('user') or {}).get('id'))) for n in nodes)


def ready():
    for _ in range(30):
        try:
            con = http.client.HTTPConnection('127.0.0.1', 3000, timeout=2)
            con.request('GET', '/admin/healthz')
            res = con.getresponse()
            if res.status == 200 and json.loads(res.read())['status'] == 'OK':
                return True
        except (OSError, ValueError):
            pass
        finally:
            try:
                con.close()
            except UnboundLocalError:
                pass
        time.sleep(1)
    return False


def main():
    before = identities()
    run('systemctl', 'start', 'headscale-backup.service')
    assert run('systemctl', 'show', 'headscale-backup.service', '-p', 'Result', '--value') == 'success'
    env = Path('/etc/headplane/runtime.env')
    previous = STAGE / 'before-language.env'
    assert not previous.exists(), 'Refusing to overwrite the deployment rollback point'
    shutil.copy2(env, previous)
    os.chmod(previous, 0o600)
    image = run('docker', 'image', 'inspect', 'headplane-local:0.8.2-bilingual-20261113', '--format', '{{.Id}}')
    lines = env.read_text().splitlines()
    assert sum(line.startswith('HEADPLANE_IMAGE=') for line in lines) == 1
    updated = '\n'.join('HEADPLANE_IMAGE=' + image if line.startswith('HEADPLANE_IMAGE=') else line for line in lines) + '\n'
    temporary = env.with_suffix('.env.zh-new')
    temporary.write_text(updated)
    os.chmod(temporary, 0o600)
    try:
        os.replace(temporary, env)
        run('systemctl', 'restart', 'headplane')
        assert ready(), 'Bilingual dashboard did not become healthy'
        assert identities() == before, 'Registered device identities changed'
        for language, cookie in [('zh-CN', ''), ('en', 'hp_language=ImVuIg%3D%3D')]:
            con = http.client.HTTPConnection('127.0.0.1', 3000, timeout=10)
            con.request('GET', '/admin/machines', headers={'Remote-User': 'admin',
                        'Remote-Email': 'admin@headplane.local', 'Cookie': cookie})
            response = con.getresponse()
            body = response.read().decode()
            con.close()
            assert response.status == 200 and f'lang="{language}"' in body, 'Language readiness failed'
    except Exception:
        shutil.copy2(previous, env)
        run('systemctl', 'restart', 'headplane')
        assert ready(), 'Rollback also failed readiness'
        raise
    (STAGE / 'deployed-image.txt').write_text(image + '\n')
    print(f'Bilingual dashboard deployed: {image}')
    print(f'Health HTTP200; {len(before)} registered device identities preserved; private rollback retained.')


if __name__ == '__main__':
    main()
