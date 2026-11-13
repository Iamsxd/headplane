#!/usr/bin/env python3
"""Guarded native-OIDC cutover with a dashboard-only rollback. Root private state."""
from importlib.machinery import SourceFileLoader
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

HERE = Path(__file__).parent
cfg = SourceFileLoader('cfg', str(HERE / 'headplane-oidc-config.py')).load_module()
verify = SourceFileLoader('verify_oidc', str(HERE / 'verify-headplane-oidc.py')).load_module()
setup = SourceFileLoader('setup', str(HERE / 'casdoor-setup.py')).load_module()
STAGE = Path('/root/headplane-optional-20261113')
ROLLBACK = STAGE / 'rollback'
DB = Path('/var/lib/headplane/hp_persist.db')
FILES = {'config.yaml': Path('/etc/headplane/config.yaml'),
    'runtime.env': Path('/etc/headplane/runtime.env'),
    'headplane.conf': Path('/etc/nginx/snippets/headplane.conf')}


def require(value, name):
    if not value:
        raise RuntimeError(name)


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def identity():
    keys = ['/etc/headscale/config.yaml', '/var/lib/headscale/noise_private.key', '/var/lib/headscale/derp_server_private.key']
    result = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in keys}
    with sqlite3.connect('file:/var/lib/headscale/db.sqlite?mode=ro', uri=True) as db:
        columns = {x[1] for x in db.execute('PRAGMA table_info(nodes)')}
        stable = [x for x in ['id', 'machine_key', 'node_key', 'user_id', 'ipv4', 'ipv6'] if x in columns]
        require('id' in stable and 'node_key' in stable and 'machine_key' in stable, 'Unexpected node schema')
        rows = db.execute('SELECT ' + ','.join(stable) + ' FROM nodes ORDER BY id').fetchall()
    result['node_identity_sha256'] = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
    result['node_count'] = len(rows)
    return result


def backup():
    output = run('python3', '/usr/local/sbin/headscale-backup.py')
    path = Path(output.split(': ', 1)[1])
    require(path.parent == Path('/var/backups/headscale') and path.is_dir(), 'Invalid backup result')
    return path


def verify_restore(snapshot):
    stage = STAGE / 'restore-check'
    stage.mkdir(mode=0o700)
    data = stage / 'data'; data.mkdir(mode=0o700)
    os.chown(data, 1000, 1000)
    shutil.copyfile(snapshot / 'casdoor.db', data / 'casdoor.db')
    os.chown(data / 'casdoor.db', 1000, 1000)
    sessions = stage / 'sessions'; sessions.mkdir(mode=0o700); os.chown(sessions, 1000, 1000)
    config = stage / 'app.conf'; shutil.copyfile(snapshot / 'casdoor-app.conf', config); os.chown(config, 1000, 1000)
    private = json.loads((snapshot / 'casdoor-credentials.json').read_text())
    try:
        for name in ['casdoor.db', 'headplane-persist.db', 'db.sqlite']:
            with sqlite3.connect('file:' + str(snapshot / name) + '?mode=ro', uri=True) as db:
                require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Backup SQLite integrity failed')
        subprocess.run(['docker', 'run', '-d', '--name', 'casdoor-restore-check', '--read-only', '--user', '1000:1000',
            '--cap-drop=ALL', '--security-opt=no-new-privileges:true', '--memory=512m', '--pids-limit=128',
            '--log-opt=max-size=5m', '--log-opt=max-file=2', '-p', '127.0.0.1:18001:8000',
            '-v', str(config) + ':/conf/app.conf:ro', '-v', str(data) + ':/var/lib/casdoor',
            '-v', str(sessions) + ':/tmp', '--tmpfs', '/logs:uid=1000,gid=1000,mode=700,size=16m',
            '--tmpfs', '/files:uid=1000,gid=1000,mode=700,size=8m', setup.IMAGE], check=True, stdout=subprocess.DEVNULL)
        api = setup.Api('http://127.0.0.1:18001/auth')
        for _ in range(60):
            try:
                api.request('/api/health'); break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError('Isolated provider restore unavailable')
        api.ok('/api/login', {'type': 'login', 'signinMethod': 'Password', 'organization': 'built-in',
            'application': 'app-built-in', 'username': 'admin', 'password': private['maintenance_password']})
        app = api.ok('/api/get-application?id=admin%2Fheadplane')
        require(app['clientId'] == private['client_id'], 'Restored client mismatch')
        user = api.ok('/api/get-user?id=headplane%2F' + private['owner_username'])
        require(user['id'] == private['owner_provider_id'] and user['isAdmin'] is False, 'Restored owner mismatch')
        api.ok('/api/logout')
    finally:
        subprocess.run(['docker', 'rm', '-f', 'casdoor-restore-check'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        require(stage.resolve() == Path('/root/headplane-optional-20261113/restore-check'), 'Unsafe restore cleanup')
        shutil.rmtree(stage)


def rollback():
    state = json.loads((ROLLBACK / 'state.json').read_text())
    subprocess.run(['systemctl', 'stop', 'headplane'], check=True)
    with sqlite3.connect(DB) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM auth_sessions')
        db.execute('UPDATE users SET sub=?,role=?,caps=?,headscale_user_id=? WHERE id=?',
            (state['owner']['sub'], state['owner']['role'], state['owner']['caps'], state['owner']['headscale_user_id'], state['owner']['id']))
    for name, target in FILES.items():
        shutil.copy2(ROLLBACK / name, target)
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'restart', 'headplane'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    require(identity() == state['network_identity'], 'Unexpected network identity after rollback')
    print('Dashboard-only rollback applied; Headscale database was not restored.')


def main():
    os.umask(0o077)
    import sys
    if sys.argv[1:] == ['rollback']:
        rollback(); return
    for name in ['provider-acceptance.json', 'oidc-acceptance.json']:
        results = json.loads((STAGE / name).read_text())
        require(results and all(x is True for x in results.values()), 'Acceptance receipt failed')
    require(not ROLLBACK.exists(), 'Existing cutover state; refusing to repeat')
    private = json.loads(Path('/etc/casdoor/credentials.json').read_text())
    with sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('SELECT * FROM users WHERE role=?', ('owner',)).fetchall()
        require(len(rows) == 1, 'Expected exactly one owner')
        owner = dict(rows[0])
        require(owner['id'] == '01M79PP6EWQXN2NKE959YGWPEX' and owner['sub'] == 'proxy:admin' and str(owner['headscale_user_id']) == '1', 'Unexpected production owner')
        require(not db.execute('SELECT 1 FROM users WHERE sub=?', (private['owner_subject'],)).fetchone(), 'Owner subject collision')
    network = identity()
    ROLLBACK.mkdir(mode=0o700)
    for name, source in FILES.items():
        shutil.copy2(source, ROLLBACK / name)
    state = {'owner': owner, 'network_identity': network, 'new_subject': private['owner_subject']}
    (ROLLBACK / 'state.json').write_text(json.dumps(state))
    snapshot = backup()
    verify_restore(snapshot)
    state['backup'] = str(snapshot)
    (ROLLBACK / 'state.json').write_text(json.dumps(state))
    changed = False
    try:
        subprocess.run(['systemctl', 'stop', 'headplane'], check=True)
        changed = True
        with sqlite3.connect(DB) as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT sub FROM users WHERE id=?', (owner['id'],)).fetchone()
            require(current == ('proxy:admin',), 'Owner changed during cutover')
            db.execute('UPDATE users SET sub=? WHERE id=? AND sub=?', (private['owner_subject'], owner['id'], 'proxy:admin'))
            db.execute('DELETE FROM auth_sessions')
        FILES['config.yaml'].write_text(cfg.render(private['client_id']))
        env = FILES['runtime.env'].read_text().splitlines()
        require(sum(x.startswith('HEADPLANE_IMAGE=') for x in env) == 1, 'Unexpected image environment')
        FILES['runtime.env'].write_text('\n'.join('HEADPLANE_IMAGE=' + cfg.IMAGE if x.startswith('HEADPLANE_IMAGE=') else x for x in env) + '\n')
        shutil.copyfile(STAGE / 'headplane-oidc-proxy.conf', FILES['headplane.conf'])
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'restart', 'headplane'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        browser = verify.Browser(production=True)
        for _ in range(60):
            try:
                status, _, _ = browser.request('/admin/login?s=logout')
                if status == 200:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError('Dashboard failed to start')
        results = verify.check_dashboard(browser)
        with sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True) as db:
            row = db.execute('SELECT id,sub,role,caps,headscale_user_id FROM users WHERE role=?', ('owner',)).fetchall()
            require(row == [(owner['id'], private['owner_subject'], owner['role'], owner['caps'], owner['headscale_user_id'])], 'Owner identity changed')
            require(db.execute("SELECT count(*) FROM auth_sessions WHERE kind='api_key'").fetchone()[0] == 0, 'API-key session found')
        results['owner_id_role_caps_link_preserved'] = True
        require(identity() == network, 'Network identities changed')
        results['headscale_devices_keys_configuration_unchanged'] = True
        for service in ['headscale', 'nginx', 'headplane', 'casdoor', 'headscale-backup.timer', 'headplane-key-rotate.timer', 'certbot-ip-renew.timer']:
            require(run('systemctl', 'is-active', service) == 'active', 'Inactive service: ' + service)
        require('127.0.0.1:18000' in run('ss', '-H', '-lnt', 'sport = :18000'), 'Provider listener mismatch')
        require('3478' in run('ss', '-H', '-lun', 'sport = :3478'), 'STUN listener missing')
        run('runuser', '-u', 'headscale', '--', 'headscale', 'configtest')
        results['services_stun_and_timers_active'] = True
        after_backup = backup()
        state['post_cutover_backup'] = str(after_backup)
        (ROLLBACK / 'state.json').write_text(json.dumps(state))
        (STAGE / 'production-acceptance.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(results, indent=2))
        print('Headplane native OIDC deployed; consistent backups and isolated provider restore verified.')
    except Exception:
        if changed:
            rollback()
        raise


if __name__ == '__main__':
    main()
