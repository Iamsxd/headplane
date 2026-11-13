#!/usr/bin/env python3
"""Read-only HTTP checks against the isolated loopback dashboard candidate."""
import http.client
from http.cookies import SimpleCookie
import re
from urllib.parse import urlsplit


def main():
    cookies = SimpleCookie()
    assets = set()
    pages = {
        '/admin/machines': ['设备', 'sun-work-tp', 'findn3', '100.64.0.3', '100.64.0.4'],
        '/admin/machines/3': ['创建时间', '100.64.0.3'],
        '/admin/users': ['用户', 'owner'],
        '/admin/dns': ['DNS', '域名'],
        '/admin/acls': ['访问'],
        '/admin/settings': ['设置', '预认证密钥'],
        '/admin/settings/auth-keys': ['认证密钥'],
        '/admin/settings/agent': ['未启用', '配置中未启用 Headplane Agent'],
    }

    def request(path, identity=True):
        headers = {'Host': '140.143.127.180', 'X-Forwarded-Proto': 'https'}
        if identity:
            headers.update({'Remote-User': 'admin', 'Remote-Email': 'admin@headplane.local',
                            'Remote-Name': 'Administrator'})
        if cookies:
            headers['Cookie'] = '; '.join(f'{key}={morsel.value}' for key, morsel in cookies.items())
        con = http.client.HTTPConnection('127.0.0.1', 3001, timeout=15)
        try:
            con.request('GET', path, headers=headers)
            res = con.getresponse()
            for key, val in res.getheaders():
                if key.lower() == 'set-cookie':
                    cookies.load(val)
            return res.status, res.read().decode()
        finally:
            con.close()

    status, body = request('/admin/healthz', False)
    assert status == 200 and 'OK' in body
    for path, markers in pages.items():
        status, body = request(path)
        assert status == 200, (path, status)
        assert 'lang="zh-CN"' in body, path
        for marker in markers:
            assert marker.lower() in body.lower(), (path, marker)
        assets.update(re.findall(r'(?:src|href)="([^"<>]+\.(?:js|css)(?:\?[^"<>]*)?)"', body))
        print(f'{path}: HTTP200, Chinese display and page-specific data confirmed')
    for asset in assets:
        url = urlsplit(asset)
        assert not url.netloc or url.netloc == '140.143.127.180'
        status, content = request(url.path)
        assert status == 200 and content, (asset, status)
    print(f'{len(assets)} referenced JS/CSS assets loaded; no mutations sent.')


if __name__ == '__main__':
    main()
