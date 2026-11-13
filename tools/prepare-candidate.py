#!/usr/bin/env python3
"""Run on the server; stage a private, loopback-only dashboard candidate."""
import os
from pathlib import Path
import sqlite3
import subprocess

STAGE = Path('/root/headplane-zh-setup-20261113')
IMAGE = 'headplane-local:0.8.2-zh-cn-20261113'


def run(*args):
    return subprocess.run(args, check=True)


def main():
    env = dict(line.split('=', 1) for line in Path('/etc/headplane/runtime.env').read_text().splitlines() if '=' in line)
    uid, gid = int(env['HEADPLANE_UID']), int(env['HEADPLANE_GID'])
    stage = STAGE / 'candidate'
    stage.mkdir(mode=0o700, exist_ok=True)
    data = stage / 'data'
    data.mkdir(mode=0o700, exist_ok=True)
    os.chown(data, uid, gid)
    with sqlite3.connect('file:/var/lib/headplane/hp_persist.db?mode=ro', uri=True) as src:
        with sqlite3.connect(data / 'hp_persist.db') as dst:
            src.backup(dst)
            assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    os.chown(data / 'hp_persist.db', uid, gid)
    os.chmod(data / 'hp_persist.db', 0o600)
    config = Path('/etc/headplane/config.yaml').read_text()
    assert 'port: 3000' in config
    config = config.replace('port: 3000', 'port: 3001', 1)
    config_path = stage / 'config.yaml'
    config_path.write_text(config)
    os.chown(config_path, 0, gid)
    os.chmod(config_path, 0o640)
    run('docker', 'run', '-d', '--name', 'headplane-zh-candidate', '--init', '--network', 'host',
        '--user', f'{uid}:{gid}', '--group-add', env['HEADSCALE_GID'], '--read-only',
        '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges', '--pids-limit', '128', '--memory', '512m',
        '--log-opt', 'max-size=5m', '--log-opt', 'max-file=2',
        '-e', 'HEADPLANE_CONFIG_PATH=/candidate-config.yaml',
        '--mount', 'type=bind,src=/etc/headplane,dst=/etc/headplane,readonly',
        '--mount', 'type=bind,src=/etc/headscale,dst=/etc/headscale,readonly',
        '--mount', f'type=bind,src={config_path},dst=/candidate-config.yaml,readonly',
        '--mount', f'type=bind,src={data},dst=/var/lib/headplane', IMAGE)
    print('Candidate started with a consistent copy of the dashboard database; port 3001.')


if __name__ == '__main__':
    main()
