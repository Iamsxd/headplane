#!/usr/bin/env python3
"""Run two disposable userspace clients to verify the embedded DERP path.

Uses official static Tailscale binaries already checksum-verified by the operator.
No system Tailscale service, TUN, DNS or routing settings are changed.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary_directory', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run as root')
    os.umask(0o077)
    test_id = uuid.uuid4().hex[:8]
    runtime = Path('/run') / f'hs-smoke-{test_id}'
    logs = Path('/root/headscale-ip-setup-20261113') / f'smoke-{test_id}'
    runtime.mkdir(mode=0o700)
    logs.mkdir(mode=0o700)
    clients, key_ids, log_handles = [], [], []
    user_id = None

    def hs(*arguments):
        result = subprocess.run(['runuser', '-u', 'headscale', '--', 'headscale', *arguments,
                                 '-o', 'json'], check=True, capture_output=True, text=True, timeout=20)
        return json.loads(result.stdout or 'null')

    def cli(index, *arguments, timeout=30):
        return subprocess.run([str(args.binary_directory / 'tailscale'),
                               '--socket=' + str(runtime / f'{index}.sock'), *arguments],
                              check=True, capture_output=True, text=True, timeout=timeout).stdout

    try:
        user = hs('users', 'create', f'ip-smoke-{test_id}')
        user_id = str(user['id'])
        for index in range(2):
            key = hs('preauthkeys', 'create', '--user', user_id, '--ephemeral', '--expiration', '15m')
            key_ids.append(str(key['id']))
            keyfile = runtime / f'{index}.auth'
            keyfile.write_text(key['key'])
            env = dict(os.environ, TS_DEBUG_ALWAYS_USE_DERP='true')
            handle = open(logs / f'client-{index}.log', 'w')
            log_handles.append(handle)
            process = subprocess.Popen([str(args.binary_directory / 'tailscaled'),
                                        '--tun=userspace-networking', '--state=mem:',
                                        '--socket=' + str(runtime / f'{index}.sock'),
                                        '--statedir=' + str(runtime / f'state-{index}'),
                                        '--port=0', '--no-logs-no-support'],
                                       env=env, stdout=handle, stderr=handle)
            clients.append(process)
            for attempt in range(100):
                if (runtime / f'{index}.sock').exists():
                    break
                if process.poll() is not None:
                    raise RuntimeError(f'Client {index} exited; see private logs')
                time.sleep(0.1)
            cli(index, 'up', '--login-server=https://140.143.127.180',
                '--auth-key=file:' + str(keyfile), '--accept-dns=false', '--accept-routes=false',
                '--netfilter-mode=off', f'--hostname=ip-smoke-{test_id}-{index}', '--timeout=30s', timeout=40)
            keyfile.unlink()
            print(f'Temporary client {index}: enrolled with trusted IP HTTPS', flush=True)
        status = json.loads(cli(1, 'status', '--json'))
        peer = status['TailscaleIPs'][0]
        for attempt in range(10):
            try:
                output = cli(0, 'ping', '--c=3', '--until-direct=false', '--timeout=5s', peer, timeout=20)
                if 'via DERP(tencent-cn)' in output:
                    print(output, flush=True)
                    break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass
            time.sleep(1)
        else:
            raise RuntimeError('No verified traffic via DERP(tencent-cn); see private logs')
        derp_map = json.loads(cli(0, 'debug', 'derp-map'))
        region = derp_map['Regions']['999']
        assert region['Nodes'][0]['HostName'] == '140.143.127.180', region
        assert not region['Nodes'][0].get('InsecureForTests', False), region
        (logs / 'result.txt').write_text(output + '\nEmbedded DERP region: ' + json.dumps(region))
        print('PASS: two disposable clients exchanged encrypted probes via self-hosted DERP.', flush=True)
        print('Both clients ran on this server; this does not replace testing two real external devices.', flush=True)
    finally:
        for process in clients:
            process.terminate()
        for process in clients:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for handle in log_handles:
            handle.close()
        if user_id is not None:
            for node in hs('nodes', 'list') or []:
                if str(node.get('user', {}).get('id')) == user_id:
                    hs('nodes', 'delete', '--identifier', str(node['id']), '--force')
            for key_id in key_ids:
                hs('preauthkeys', 'delete', '--id', key_id)
            hs('users', 'destroy', '--identifier', user_id, '--force')
        shutil.rmtree(runtime)
        print('Temporary clients, authorization keys and test user cleaned up.', flush=True)


if __name__ == '__main__':
    main()
