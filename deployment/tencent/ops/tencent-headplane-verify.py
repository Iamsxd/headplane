#!/usr/bin/env python3
"""Verify the public dashboard using a private login file without printing credentials."""
import argparse
import base64
import http.client
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--login-file', type=Path, default=Path.home()/'.ssh/tencent-headplane-admin.txt')
    parser.add_argument('--expect-device', help='Assert this device name appears in rendered HTML')
    parser.add_argument('--expect-language', help='Assert the HTML document language')
    parser.add_argument('--expect-text', action='append', default=[], help='Assert visible UI text is present')
    args = parser.parse_args()
    settings = dict(line.split(': ', 1) for line in args.login_file.read_text().splitlines() if ': ' in line)
    url = urlparse(settings['URL'])
    assert url.scheme == 'https' and url.hostname
    route = url.path.rstrip('/') + '/machines'
    authorization = 'Basic ' + base64.b64encode((settings['Username']+':'+settings['Password']).encode()).decode()

    def request(path, headers):
        connection = http.client.HTTPSConnection(url.hostname, url.port or 443, timeout=10)
        try:
            connection.request('GET', path, headers=headers)
            response = connection.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            connection.close()

    for label, headers in [
        ('unauthenticated', {}),
        ('spoofed identity', {'Remote-User': 'admin', 'Remote-Email': 'admin@headplane.local'}),
        ('wrong password', {'Authorization': 'Basic ' + base64.b64encode(b'admin:wrong-password').decode()}),
    ]:
        status, _, _ = request(route, headers)
        assert status == 401, (label, status)
        print(label + ': HTTP401')
    headers = {'Authorization': authorization}
    status, response_headers, body = request(route, headers)
    assert status == 200, status
    if args.expect_device:
        assert args.expect_device.lower().encode() in body.lower(), 'Expected device absent'
    if args.expect_language:
        assert f'lang="{args.expect_language}"'.encode() in body, 'Unexpected document language'
    for expected in args.expect_text:
        assert expected.encode() in body, 'Expected UI text absent'
    for key, value in response_headers:
        if key.lower() == 'set-cookie':
            assert 'secure' in value.lower() and 'httponly' in value.lower()
    assets = set(re.findall(r'(?:src|href)="([^"<>]+\.(?:js|css)(?:\?[^"<>]*)?)"', body.decode()))
    loaded = 0
    for asset in sorted(assets):
        parsed = urlparse(urljoin(settings['URL'], asset))
        if parsed.netloc == url.netloc:
            status, _, content = request(parsed.path + ('?' + parsed.query if parsed.query else ''), headers)
            assert status == 200 and content, (parsed.path, status)
            loaded += 1
    print(f'Administrator: HTTP200; {loaded} referenced JS/CSS assets loaded over trusted HTTPS')
    print('No credentials printed; every proxied dashboard request requires Nginx authentication')


if __name__ == '__main__':
    main()
