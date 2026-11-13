#!/usr/bin/env python3
"""Exercise remembered language changes against a private loopback candidate."""
import argparse
import base64
import concurrent.futures
import http.client
from http.cookies import SimpleCookie
import re
from pathlib import Path
from urllib.parse import urlencode, urlsplit

connection_class = http.client.HTTPConnection
connection_host = '127.0.0.1'
connection_port = 3001
public_authorization = None
public_host = '140.143.127.180'
public_origin = 'https://140.143.127.180'


def request(path, cookie='', form=None, origin=None):
    con = connection_class(connection_host, connection_port, timeout=15)
    headers = {'Host': public_host, 'Cookie': cookie}
    if public_authorization:
        headers['Authorization'] = public_authorization
    else:
        headers.update({'X-Forwarded-Proto': 'https', 'Remote-User': 'admin',
                        'Remote-Email': 'admin@headplane.local', 'Remote-Name': 'Administrator'})
    if form is not None:
        headers.update({'Content-Type': 'application/x-www-form-urlencoded', 'Origin': origin or public_origin})
    try:
        con.request('POST' if form is not None else 'GET', path,
                    urlencode(form) if form is not None else None, headers)
        response = con.getresponse()
        return response.status, {key.lower(): value for key, value in response.getheaders()}, response.read().decode()
    finally:
        con.close()


def switch(language, return_to='/machines?status=offline', cookie=''):
    status, headers, _ = request('/admin/api/language', cookie,
                                 {'language': language, 'returnTo': return_to})
    assert status == 303, ('language POST', status)
    assert headers.get('location') == '/admin' + return_to, headers.get('location')
    values = SimpleCookie()
    values.load(headers['set-cookie'])
    preference = values['hp_language']
    assert preference['secure'] and preference['httponly']
    assert preference['samesite'].lower() == 'lax' and preference['path'] == '/admin'
    assert int(preference['max-age']) == 31536000
    return f'hp_language={preference.value}'


def main():
    global connection_class, connection_host, connection_port
    global public_authorization, public_host, public_origin
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public', action='store_true', help='Verify production through trusted HTTPS')
    parser.add_argument('--login-file', type=Path, default=Path.home()/'.ssh/tencent-headplane-admin.txt')
    args = parser.parse_args()
    if args.public:
        settings = dict(line.split(': ', 1) for line in args.login_file.read_text().splitlines() if ': ' in line)
        url = urlsplit(settings['URL'])
        assert url.scheme == 'https' and url.hostname
        connection_class = http.client.HTTPSConnection
        connection_host, connection_port = url.hostname, url.port or 443
        public_host, public_origin = url.netloc, 'https://' + url.netloc
        token = (settings['Username'] + ':' + settings['Password']).encode()
        public_authorization = 'Basic ' + base64.b64encode(token).decode()
    english = switch('en')
    chinese = switch('zh-CN', cookie=english)
    print('Language POST, cookie security/one-year persistence, current filter redirect: passed')
    for cookie in ['', 'hp_language=broken', 'hp_language=ImZyIg%3D%3D']:
        status, _, body = request('/admin/machines', cookie)
        assert status == 200 and 'lang="zh-CN"' in body and '添加设备' in body
    print('Missing, damaged and unsupported language cookies fall back to Chinese')
    pages = {
        '/machines': ('添加设备', 'Add Device'),
        '/machines/3': ('创建时间', 'Created'),
        '/users': ('添加用户', 'Add user'),
        '/dns': ('搜索域', 'Search domains'),
        '/acls': ('访问控制', 'Access Control'),
        '/settings': ('设置', 'Settings'),
        '/settings/auth-keys': ('认证密钥', 'keys'),
        '/settings/agent': ('配置中未启用 Headplane Agent', 'Agent is not enabled'),
    }
    for cookie, language, index in [(chinese, 'zh-CN', 0), (english, 'en', 1)]:
        assets = set()
        for path, labels in pages.items():
            status, _, body = request('/admin' + path, cookie)
            assert status == 200 and f'lang="{language}"' in body, (path, language, status)
            assert labels[index].lower() in body.lower(), (path, language, labels[index])
            assets.update(re.findall(r'(?:src|href)="([^"<>]+\.(?:js|css)(?:\?[^"<>]*)?)"', body))
        status, _, body = request('/admin/machines', cookie)
        for value in ['sun-work-tp', 'findn3', '100.64.0.3', '100.64.0.4']:
            assert value in body.lower()
        assert ('Add Device' not in body) if language == 'zh-CN' else ('添加设备' not in body)
        for asset in assets:
            url = urlsplit(asset)
            assert not url.netloc or url.netloc == public_host
            # Old documents remain loadable after another tab switches language.
            status, _, content = request(url.path, english if index == 0 else chinese)
            assert status == 200 and content, (asset, language, status)
        print(f'{language}: {len(assets)} referenced assets load even with the other language cookie')
        # Match the UI's fetcher submission; the missing username prevents any write.
        status, _, body = request('/admin/users.data', cookie, {'action_id': 'create_user'})
        assert status == 400 and ('username' in body), ('validation action', language, status)
    print('Eight pages in each language and both existing device identities: passed')
    for value in ['fr', '', 'EN', 'en-US']:
        status, headers, _ = request('/admin/api/language', form={'language': value})
        assert status == 400 and 'set-cookie' not in headers, (value, status)
    for path in ['//evil.example', 'https://evil.example', '/\\evil.example', '/../outside',
                 '/x\r\nLocation: https://evil.example', '/%2e%2e/outside',
                 '/x/..//evil.example', '/.//evil.example', '/a/%2e%2e//evil.example']:
        status, headers, _ = request('/admin/api/language', form={'language': 'en', 'returnTo': path})
        assert status == 303 and headers['location'] == '/admin/', (path, status, headers.get('location'))
    status, headers, _ = request('/admin/api/language', form={'language': 'en'}, origin='https://evil.example')
    assert status in (400, 403) and 'set-cookie' not in headers, ('CSRF', status)
    print('Invalid input, unsafe redirect and cross-origin POST rejection: passed')
    work = [(english, 'en'), (chinese, 'zh-CN')] * 8
    def check(item):
        cookie, language = item
        status, _, body = request('/admin/machines', cookie)
        assert status == 200 and f'lang="{language}"' in body
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(check, work))
    print('Concurrent language requests remain isolated: passed')
    if args.public:
        print('Public language switching verified over trusted HTTPS; no credentials printed')


if __name__ == '__main__':
    main()
