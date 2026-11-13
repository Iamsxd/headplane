#!/usr/bin/env python3
"""Temporary read-only local UI preview over an existing SSH tunnel; no passwords."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Preview(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        if not self.path.startswith('/admin/'):
            self.send_error(404)
            return
        # The preview only displays pages; production live updates are checked separately.
        if self.path.startswith('/admin/events/'):
            self.send_response(204)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        con = http.client.HTTPConnection('127.0.0.1', 18882, timeout=15)
        try:
            con.request('GET', self.path, headers={
                'Host': '140.143.127.180', 'X-Forwarded-Proto': 'https',
                'Remote-User': 'admin', 'Remote-Email': 'admin@headplane.local',
                'Remote-Name': 'Administrator',
            })
            res = con.getresponse()
            body = res.read()
            self.send_response(res.status)
            for key, val in res.getheaders():
                if key.lower() not in {'connection', 'transfer-encoding', 'content-length', 'set-cookie'}:
                    self.send_header(key, val)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        finally:
            con.close()

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    print('Read-only preview: http://127.0.0.1:18883/admin/machines', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 18883), Preview).serve_forever()
