"""Single-user localhost Google connection; credentials exist only in process memory."""
import os
import secrets
import threading
import time
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPE = 'https://www.googleapis.com/auth/calendar.events.freebusy'
REDIRECT = 'http://127.0.0.1:8080/oauth/callback'
lock = threading.Lock()
credentials = None
pending = {}
client_config = None


def configure(config):
    global client_config
    web = config.get('web')
    if not isinstance(web, dict) or not web.get('client_id', '').endswith('.apps.googleusercontent.com') or not web.get('client_secret'):
        raise ValueError('Use a Google Cloud Web application OAuth client JSON file.')
    if REDIRECT not in web.get('redirect_uris', []):
        raise ValueError('Add http://127.0.0.1:8080/oauth/callback to the Google client redirect URIs.')
    with lock:
        disconnect_unlocked()
        client_config = {'web': {'client_id': web['client_id'], 'client_secret': web['client_secret'],
                       'auth_uri': 'https://accounts.google.com/o/oauth2/auth', 'token_uri': 'https://oauth2.googleapis.com/token'}}


def status():
    return {'configured': bool(client_config or (os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'))),
            'connected': credentials is not None, 'scope': 'Busy times only; no event titles or calendar edits.'}


def authorize():
    if not status()['configured']:
        raise ValueError('Google OAuth setup is required. See README: Google Calendar setup. The Codex calendar connection is separate from this local app.')
    state = secrets.token_urlsafe(32)
    flow = Flow.from_client_config(client_config or {'web': {
        'client_id': os.environ['GOOGLE_CLIENT_ID'], 'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token'}}, scopes=[SCOPE], state=state, redirect_uri=REDIRECT, autogenerate_code_verifier=True)
    url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    with lock:
        pending.clear()
        pending[state] = (flow, time.monotonic())
    return url


def finish(query):
    global credentials
    data = parse_qs(query)
    state = data.get('state', [''])[0]
    with lock:
        record = pending.pop(state, None)
    if not record or time.monotonic() - record[1] > 600:
        raise ValueError('Calendar connection expired. Try again.')
    if 'error' in data or not data.get('code'):
        raise ValueError('Calendar permission was not granted.')
    flow = record[0]
    flow.fetch_token(code=data['code'][0])
    with lock:
        credentials = flow.credentials


def disconnect():
    with lock:
        disconnect_unlocked()


def disconnect_unlocked():
    global credentials
    credentials = None
    pending.clear()


def busy(start, end):
    with lock:
        if credentials is None:
            raise ValueError('Connect Google Calendar before scanning your schedule.')
        service = build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        ids = [x.strip() for x in os.environ.get('GOOGLE_CALENDAR_IDS', 'primary').split(',') if x.strip()]
        response = service.freebusy().query(body={'timeMin': start.isoformat(), 'timeMax': end.isoformat(),
                  'timeZone': 'America/Los_Angeles', 'items': [{'id': i} for i in ids]}).execute()
    from city_planner import parse_time
    output = []
    for i in ids:
        calendar = response.get('calendars', {}).get(i)
        if calendar is None or calendar.get('errors'):
            raise ValueError('Could not read all selected calendars; no gap was assumed free.')
        output.extend((parse_time(b['start']), parse_time(b['end'])) for b in calendar.get('busy', []))
    return output
