"""Local UI for ScoopScout. Run: python3 server.py"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import time
import agent
import city_planner
import google_calendar
from urllib.parse import urlparse


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Calendar data and OAuth callback codes never enter logs.

    def respond(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get('Host') not in ('127.0.0.1:8080', 'localhost:8080'):
            return self.respond(403, {'error': 'Local access only'})
        if self.path in ('/demo', '/demo/ScoopScout-demo.mp4'):
            name = 'presentation.html' if self.path == '/demo' else 'ScoopScout-demo.mp4'
            body = Path(__file__).with_name('demo').joinpath(name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8' if name.endswith('.html') else 'video/mp4')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/api/calendar/status':
            return self.respond(200, google_calendar.status())
        if self.path.startswith('/oauth/callback?'):
            try:
                google_calendar.finish(urlparse(self.path).query)
                self.send_response(303)
                self.send_header('Location', '/')
                self.end_headers()
            except ValueError as exc:
                self.respond(400, {'error': str(exc)})
            except Exception:
                self.respond(502, {'error': 'Google authorization failed. Try reconnecting.'})
            return
        if self.path == '/api/catalog':
            return self.respond(200, agent.CATALOG)
        if self.path not in ('/', '/index.html'):
            return self.respond(404, {'error': 'Not found'})
        body = Path(__file__).with_name('index.html').read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.headers.get('Origin') not in ('http://127.0.0.1:8080', 'http://localhost:8080') or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.respond(403, {'error': 'Use the local app to make this request.'})
        if self.path == '/api/calendar/connect':
            try:
                return self.respond(200, {'url': google_calendar.authorize()})
            except ValueError as exc:
                return self.respond(400, {'error': str(exc)})
        if self.path == '/api/calendar/disconnect':
            google_calendar.disconnect()
            return self.respond(200, {'connected': False})
        if self.path == '/api/calendar/configure':
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length < 20000:
                    raise ValueError('Choose a small Google OAuth client JSON file.')
                google_calendar.configure(json.loads(self.rfile.read(length)))
                return self.respond(200, google_calendar.status())
            except (ValueError, TypeError, KeyError) as exc:
                return self.respond(400, {'error': str(exc)})
        if self.path not in ('/api/recommend', '/api/day'):
            return self.respond(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 1000000:
                return self.respond(400, {'error': 'Request is too large or empty.'})
            data = json.loads(self.rfile.read(length))
            if self.path == '/api/day':
                start, end = city_planner.parse_time(data['start']), city_planner.parse_time(data['end'])
                if end <= start or end - start > city_planner.timedelta(hours=24):
                    raise ValueError('Choose a planning window of no more than one day.')
                if data.get('mode') == 'google':
                    busy = google_calendar.busy(start, end)
                elif data.get('mode') == 'manual':
                    busy = [(city_planner.parse_time(b['start']), city_planner.parse_time(b['end'])) for b in data.get('busy', [])]
                    if any(b <= a for a,b in busy):
                        raise ValueError('Busy intervals must end after they begin.')
                else:
                    raise ValueError('Select Google Calendar or manual busy times.')
                started = time.monotonic()
                result = city_planner.plan_day(data, busy)
                result['calendar_source'] = 'Google Calendar' if data['mode'] == 'google' else 'Manual busy times'
                result['elapsed_seconds'] = round(time.monotonic()-started, 2)
                return self.respond(200, result)
            query = data.get('query', '').strip()
            if not query or len(query) > 2000:
                return self.respond(400, {'error': 'Enter a request under 2,000 characters.'})
            started = time.monotonic()
            result = agent.plan_break(query, data['break_minutes']) if 'break_minutes' in data else agent.recommend(query, data.get('max_walk'), structured=True)
            result['elapsed_seconds'] = round(time.monotonic() - started, 2)
            self.respond(200, result)
        except (ValueError, KeyError, TypeError) as exc:
            self.respond(400, {'error': str(exc)})
        except Exception:
            self.respond(503, {'error': 'The agent could not complete this request. Check the workshop model connection and try again.'})


if __name__ == '__main__':
    print('ScoopScout: http://127.0.0.1:8080', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8080), Handler).serve_forever()
