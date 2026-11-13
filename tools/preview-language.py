#!/usr/bin/env python3
"""Private loopback preview: GET pages and language-cookie POST only, via SSH."""
import http.client
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Preview(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        if not self.path.startswith('/admin/'):
            self.send_error(404)
            return
        if self.path.startswith('/admin/events/'):
            self.send_response(204)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.forward()

    def do_POST(self):
        if self.path != '/admin/api/language':
            self.send_error(405)
            return
        size = int(self.headers.get('Content-Length', '0'))
        if not 0 <= size <= 4096:
            self.send_error(413)
            return
        self.forward(self.rfile.read(size))

    def forward(self, body=None):
        cookies = SimpleCookie()
        cookies.load(self.headers.get('Cookie', ''))
        preference = cookies.get('hp_language')
        headers = {'Host': '140.143.127.180', 'X-Forwarded-Proto': 'https',
                   'Remote-User': 'admin', 'Remote-Email': 'admin@headplane.local',
                   'Remote-Name': 'Administrator'}
        if preference:
            headers['Cookie'] = f'hp_language={preference.value}'
        if body is not None:
            headers['Content-Type'] = self.headers.get('Content-Type', 'application/x-www-form-urlencoded')
            origin = self.headers.get('Origin', '')
            headers['Origin'] = ('https://140.143.127.180' if origin in {
                'http://127.0.0.1:18883', 'http://localhost:18883'} else origin)
        con = http.client.HTTPConnection('127.0.0.1', 18882, timeout=15)
        try:
            con.request('POST' if body is not None else 'GET', self.path, body, headers)
            res = con.getresponse()
            content = res.read()
            self.send_response(res.status)
            for key, value in res.getheaders():
                if key.lower() == 'set-cookie':
                    # Never expose dashboard/session credentials through the preview.
                    if value.startswith('hp_language='):
                        self.send_header(key, value)
                elif key.lower() not in {'connection', 'transfer-encoding', 'content-length'}:
                    self.send_header(key, value)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(content)
        finally:
            con.close()

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    print('Local preview: http://127.0.0.1:18883/admin/machines', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 18883), Preview).serve_forever()
