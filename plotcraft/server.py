"""Local-only HTTP server. Static paths are allowlisted; rendering is serialized."""
import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from . import __version__
from .model import default_project, validate
from .render import render

STATIC = Path(__file__).parent / 'static'
MAX_BODY = 1_000_000


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type='application/json'):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, allow_nan=False).encode()
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def trusted(self):
        # Reject DNS rebinding and browser requests from unrelated origins.
        host = self.headers.get('Host', '')
        expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        return host in expected and self.headers.get('Origin', f'http://{host}') == f'http://{host}'

    def do_GET(self):
        if not self.trusted():
            return self.reply(403, {'error': 'Use the localhost URL printed by Plotcraft'})
        path = urlsplit(self.path).path
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path in files:
            name, kind = files[path]
            return self.reply(200, (STATIC / name).read_bytes(), kind)
        if path == '/api/default':
            return self.reply(200, default_project())
        if path == '/api/health':
            return self.reply(200, {'status': 'ok', 'version': __version__})
        self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.trusted():
            return self.reply(403, {'error': 'Cross-origin requests are not allowed'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, {'error': 'Send application/json'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {'error': 'Request must be under 1 MB'})
            data = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if path == '/api/validate':
                return self.reply(200, validate(data))
            if path == '/api/csv':
                if not isinstance(data, dict) or not isinstance(data.get('csv'), str):
                    raise ValueError('Expected CSV text')
                rows = list(csv.reader(io.StringIO(data['csv'].lstrip('\ufeff'))))
                if len(rows) < 2:
                    raise ValueError('CSV needs a header and at least one data row')
                p = default_project()
                p.update(headers=rows[0], cells=rows[1:], cellStyles={})
                p['chart']['series'] = list(range(1, len(rows[0])))
                return self.reply(200, validate(p))
            if path in ('/api/render', '/api/export'):
                if not isinstance(data, dict):
                    raise ValueError('Expected a project')
                fmt = data.get('format', 'svg') if path == '/api/export' else 'svg'
                output, values, errors = render(data.get('project'), fmt)
                if path == '/api/render':
                    return self.reply(200, {'svg': output.decode() if output else None, 'values': values, 'errors': errors})
                if errors:
                    return self.reply(422, {'error': 'Fix data errors before exporting', 'errors': errors})
                return self.reply(200, output, {'svg': 'image/svg+xml', 'png': 'image/png', 'pdf': 'application/pdf'}[fmt])
            self.reply(404, {'error': 'Not found'})
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            self.reply(400, {'error': str(exc) or 'Invalid request'})


def main():
    parser = argparse.ArgumentParser(description='Plotcraft local chart studio')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.daemon_threads = True
    print(f'Plotcraft {__version__} · Open http://127.0.0.1:{server.server_port} · Ctrl+C to stop', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
