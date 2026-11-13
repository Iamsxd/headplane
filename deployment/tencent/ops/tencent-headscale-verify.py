#!/usr/bin/env python3
"""Check Headscale/TLS/DERP/STUN locally or through the public endpoint."""
import argparse
import http.client
import json
import os
import socket
import ssl
import struct
import subprocess
import zlib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--public', action='store_true', help='Check production HTTPS and listeners')
parser.add_argument('--remote', action='store_true', help='Check public protocols from another host; skip local configuration checks')
parser.add_argument('--server-name', default='hs.lovecanl.cn', help='TLS certificate name/IP and HTTP Host')
parser.add_argument('--host', help='Override connection host; certificate validation still uses --server-name')
args = parser.parse_args()
public = args.public or args.remote
host = args.host or (args.server_name if args.remote else '127.0.0.1')


def connect_tls():
    context = ssl.create_default_context(cafile=None if public else '/etc/headscale/tls-preview/cert.pem')
    raw = socket.create_connection((host, 443 if public else 18443), timeout=8)
    return context.wrap_socket(raw, server_hostname=args.server_name)


def request(path):
    with connect_tls() as stream:
        stream.sendall((f'GET {path} HTTP/1.1\r\nHost: {args.server_name}\r\n'
                        'Connection: close\r\n\r\n').encode())
        response = http.client.HTTPResponse(stream)
        response.begin()
        assert response.status == 200, (path, response.status)
        return json.loads(response.read())


def check_derp():
    with connect_tls() as stream:
        stream.sendall((f'GET /derp HTTP/1.1\r\nHost: {args.server_name}\r\n'
                       'Connection: Upgrade\r\nUpgrade: DERP\r\n\r\n').encode())
        received = b''
        while b'\r\n\r\n' not in received:
            chunk = stream.recv(4096)
            assert chunk, 'DERP closed before HTTP upgrade'
            received += chunk
            assert len(received) < 65536, 'Invalid DERP HTTP header'
        headers, frame = received.split(b'\r\n\r\n', 1)
        assert headers.split(b'\r\n')[0].startswith(b'HTTP/1.1 101'), headers
        while len(frame) < 5:
            chunk = stream.recv(4096)
            assert chunk, 'DERP frame header missing'
            frame += chunk
        frame_type, frame_length = struct.unpack('!BI', frame[:5])
        assert frame_type == 1 and 32 <= frame_length <= 256, (frame_type, frame_length)
        while len(frame) < 5 + frame_length:
            chunk = stream.recv(4096)
            assert chunk, 'DERP server-key frame truncated'
            frame += chunk
        return 'HTTP 101 and DERP server-key frame received'


def check_control_route():
    with connect_tls() as stream:
        stream.sendall((f'POST /ts2021 HTTP/1.1\r\nHost: {args.server_name}\r\n'
                       'Connection: Upgrade\r\nUpgrade: tailscale-control-protocol\r\n'
                       'Content-Length: 0\r\n\r\n').encode())
        # This probe has no Noise handshake. The real Headscale handler must
        # reject it, proving POST routing without claiming client authentication.
        response = http.client.HTTPResponse(stream)
        response.begin()
        body = response.read()
        assert response.status == 400 and b'missing Tailscale handshake header' in body
        return 'Unsigned POST control request rejected by Headscale as expected'


def check_stun():
    transaction = os.urandom(12)
    # Tailscale requires its SOFTWARE marker and a final FINGERPRINT attribute.
    software = struct.pack('!HH', 0x8022, 8) + b'tailnode'
    message = struct.pack('!HHI', 1, len(software) + 8, 0x2112A442) + transaction + software
    fingerprint = zlib.crc32(message) ^ 0x5354554E
    message += struct.pack('!HHI', 0x8028, 4, fingerprint)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(8)
        client.sendto(message, (host, 3478))
        response, _ = client.recvfrom(4096)
    assert len(response) >= 20, 'STUN header missing'
    kind, length, cookie = struct.unpack('!HHI', response[:8])
    assert kind == 0x0101 and cookie == 0x2112A442, (kind, cookie)
    assert response[8:20] == transaction and len(response) == 20 + length
    return 'Binding success response with matching transaction'


def check_listeners():
    lines = subprocess.check_output(['ss', '-H', '-lntu'], text=True).splitlines()
    expected = {8081, 9090, 18443, 3478}
    if os.path.exists('/etc/headplane/config.yaml'):
        expected.add(3000)
    if public:
        expected.add(443)
    private_ports = {3000, 8081, 9090, 18443, 50443} | (set() if public else {3478})
    seen = set()
    for line in lines:
        address = line.split()[4]
        port = int(address.rsplit(':', 1)[1])
        if not public:
            assert port not in {80, 443}, 'Unexpected public website entry'
        if port in private_ports:
            assert address.startswith('127.0.0.1:'), address
        if port in expected:
            seen.add(port)
        if public and port in {443, 3478}:
            assert address in {f'0.0.0.0:{port}', f'*:{port}', f'[::]:{port}'}, address
    assert seen == expected, (seen, expected)
    return ('HTTPS and STUN public; backend and metrics loopback only' if public
            else 'All Headscale endpoints use loopback; 80/443 closed')


if not args.remote:
    subprocess.run(['runuser', '-u', 'headscale', '--', 'headscale', 'configtest'],
                   check=True, capture_output=True)
result = {
    'health': request('/health'),
    'control_key_fields': sorted(request('/key?v=130')),
    'control_route': check_control_route(),
    'derp': check_derp(),
    'stun': check_stun(),
}
if not args.remote:
    result['listeners'] = check_listeners()
print(json.dumps(result, ensure_ascii=False, indent=2))
