"""The study app on a desktop: serves <data>/app/ and saves progress beside it.

    python3 app/server.py                                   # http://127.0.0.1:8742, data in $TIBETAN_DATA or the default below
    python3 app/server.py --port 8743 --root DIR --device test   # a throwaway copy for testing

Same contract as the phone's bridge (android/): read a file, list a folder, append to this device's
progress log, write a pasted class note into inbox/. Nothing else is writable. Localhost only.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

def _arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


ROOT = os.path.realpath(os.path.expanduser(_arg('--root', os.environ.get('TIBETAN_DATA') or '~/tibetan-data')))
DEVICE = _arg('--device', 'desktop')
PORT = int(_arg('--port', '8742'))
READABLE = ('app/', 'progress/', 'inbox/')


def inside(rel):
    p = os.path.realpath(os.path.join(ROOT, rel))
    return p if p.startswith(ROOT + os.sep) else None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype='text/plain; charset=utf-8'):
        b = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ('/', '/index.html'):
            p = inside('app/index.html')
            return self.send(200, open(p, 'rb').read(), 'text/html; charset=utf-8') if p and os.path.exists(p) else self.send(404, 'not built')
        if u.path == '/api/device':
            return self.send(200, DEVICE)
        if u.path == '/api/read':
            rel = q.get('p', [''])[0]
            p = inside(rel)
            if not p or not rel.startswith(READABLE) or not os.path.isfile(p):
                return self.send(404, '')
            return self.send(200, open(p, 'rb').read())
        if u.path == '/api/list':
            rel = q.get('d', [''])[0].strip('/')
            p = inside(rel)
            if not p or rel + '/' not in READABLE or not os.path.isdir(p):
                return self.send(200, '[]', 'application/json')
            return self.send(200, json.dumps(sorted(f for f in os.listdir(p) if not f.startswith('.'))), 'application/json')
        self.send(404, '')

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get('Content-Length') or 0)
        try:
            data = json.loads(self.rfile.read(n) or b'{}')
        except ValueError:
            return self.send(400, 'bad json')
        rel, text = data.get('p', ''), data.get('text', '')
        if u.path == '/api/append':
            if rel != f'progress/{DEVICE}.jsonl':
                return self.send(403, 'only this device\'s progress log')
            p = inside(rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'a', encoding='utf-8') as f:
                f.write(text)
            return self.send(200, 'ok')
        if u.path == '/api/write':
            if not (rel.startswith('inbox/') and rel.endswith('.txt') and '/' not in rel[6:]):
                return self.send(403, 'only inbox notes')
            p = inside(rel)
            if os.path.exists(p):
                return self.send(409, 'exists')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(text)
            return self.send(200, 'ok')
        self.send(404, '')


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H)
    print(f'Tibetan study app on http://127.0.0.1:{PORT} — data in {ROOT}', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
