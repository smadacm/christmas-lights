from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse
import uuid

from jinja2 import Environment, FileSystemLoader
import requests

from scheduler import CronScheduler

HERE = Path(__file__).parent.resolve()
DATA_DIR = Path(os.environ.get('DATA_DIR', str(HERE))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
CLIENTS_FILE = DATA_DIR / 'clients.json'
SCHEDULE_FILE = DATA_DIR / 'schedule.json'
TEMPLATES_DIR = HERE / 'templates'

env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

AVAILABLE_ACTIONS = [
  {'name': 'off', 'label': 'Off', 'kind': 'pattern', 'params': {}},
  {'name': 'basic', 'label': 'Basic', 'kind': 'pattern', 'params': {}},
  {'name': 'demo', 'label': 'Demo', 'kind': 'pattern', 'params': {}},
  {'name': 'rainbow', 'label': 'Rainbow', 'kind': 'pattern', 'params': {'step': 8, 'sleep_ms': 50}},
  {'name': 'chase', 'label': 'Candy Cane', 'kind': 'pattern', 'params': {'palette': ['#ff0000', '#ffffff'], 'block_size': 4, 'sleep_ms': 120}},
  {'name': 'chase', 'label': 'Christmas Chase', 'kind': 'pattern', 'params': {'palette': ['#ff0000', '#00ff00', '#ffffff'], 'block_size': 1, 'sleep_ms': 180}},
  {'name': 'wipe', 'label': 'Red Green Wipe', 'kind': 'pattern', 'params': {'palette': ['#ff0000', '#00ff00'], 'edge': 6, 'step': 1, 'pause_frames': 13, 'sleep_ms': 15}},
  {'name': 'wipe_shoot', 'label': 'Red Green Wipe & Shoot', 'kind': 'pattern', 'params': {'palette': ['#ff0000', '#00ff00'], 'shoot_count': 3, 'edge': 6, 'wipe_step': 2, 'shoot_width': 10, 'shoot_step': 3, 'sleep_ms': 15}},
  {'name': 'shooting', 'label': 'Red Green Shooting', 'kind': 'pattern', 'params': {'palette': ['#ff0000', '#00ff00'], 'sleep_ms': 25}},
  {'name': 'twinkle', 'label': 'Twinkle', 'kind': 'pattern', 'params': {'spawn_count': 3, 'fade_step': 16, 'sleep_ms': 40, 'palette': ['#ff0000', '#00ff00', '#ffffff', '#ffb400']}},
  {'name': 'twinkle', 'label': 'Super Twinkle', 'kind': 'pattern', 'params': {'spawn_count': 10, 'fade_step': 36, 'sleep_ms': 20, 'palette': ['#ff0000', '#00ff00', '#ffffff', '#ffb400']}},
  {'name': 'brightness', 'label': 'Brightness Mod', 'kind': 'mod', 'params': {'level': 50}},
  {'name': 'wave', 'label': 'Wave Mod', 'kind': 'mod', 'params': {'direction': 1, 'min_brightness': 20, 'max_brightness': 100, 'width': 20}},
  {'name': 'twinkle_mod', 'label': 'Twinkle Mod', 'kind': 'mod', 'params': {'count': 5, 'speed': 1}},
]


def load_clients():
  if not CLIENTS_FILE.exists():
    return []
  try:
    with CLIENTS_FILE.open() as fd:
      data = json.load(fd)
    clients = data.get('clients', [])
    return clients if isinstance(clients, list) else []
  except (OSError, ValueError):
    return []


def save_clients(clients):
  with CLIENTS_FILE.open('w') as fd:
    json.dump({'clients': clients}, fd, indent=2)


def find_client(client_id):
  for client in load_clients():
    if client.get('id') == client_id:
      return client
  return None


def normalize_url(url):
  url = (url or '').strip().rstrip('/')
  if url and not url.startswith('http://') and not url.startswith('https://'):
    url = 'http://' + url
  return url


class LightsUIHandler(BaseHTTPRequestHandler):
  def _send_json(self, data, status=200):
    body = json.dumps(data).encode('utf-8')
    self.send_response(status)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def _send_html(self, html, status=200):
    body = html.encode('utf-8')
    self.send_response(status)
    self.send_header('Content-Type', 'text/html; charset=utf-8')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def _read_json_body(self):
    length = int(self.headers.get('Content-Length', '0') or 0)
    raw = self.rfile.read(length) if length > 0 else b'{}'
    return json.loads(raw.decode('utf-8'))

  def do_GET(self):
    path = urlparse(self.path).path

    if path == '/':
      template = env.get_template('index.html')
      html = template.render(
        clients_json=json.dumps(load_clients()),
        actions_json=json.dumps(AVAILABLE_ACTIONS),
      )
      self._send_html(html)
      return

    if path == '/schedule':
      template = env.get_template('schedule.html')
      html = template.render(
        clients_json=json.dumps(load_clients()),
        actions_json=json.dumps(AVAILABLE_ACTIONS),
        jobs_json=json.dumps(self.server.scheduler.load_jobs()),
      )
      self._send_html(html)
      return

    if path == '/api/schedule':
      self._send_json({'jobs': self.server.scheduler.load_jobs()})
      return

    if path == '/api/clients':
      self._send_json({'clients': load_clients()})
      return

    parts = [p for p in path.split('/') if p]
    if len(parts) == 4 and parts[0] == 'api' and parts[1] == 'clients':
      client_id, action = parts[2], parts[3]
      client = find_client(client_id)
      if client is None:
        self._send_json({'error': 'Client not found'}, status=404)
        return

      if action == 'status':
        try:
          res = requests.get(client['url'] + '/', timeout=3)
          self._send_json({'online': res.ok, 'info': res.json()})
        except Exception as exc:
          self._send_json({'online': False, 'error': str(exc)}, status=502)
        return

      if action == 'lights':
        try:
          res = requests.get(client['url'] + '/lights', timeout=3)
          self._send_json(res.json(), status=res.status_code)
        except Exception as exc:
          self._send_json({'error': str(exc)}, status=502)
        return

    self._send_json({'error': 'Not Found'}, status=404)

  def do_POST(self):
    path = urlparse(self.path).path

    if path == '/api/reload':
      self._send_json({'ok': True, 'reloading': True})
      server = self.server

      def _reexec():
        try:
          server.shutdown()
          server.server_close()
        except Exception:
          pass
        os.execv(sys.executable, [sys.executable] + sys.argv)

      threading.Timer(0.2, _reexec).start()
      return

    if path == '/api/schedule':
      try:
        payload = self._read_json_body()
        jobs = payload.get('jobs', [])
        count = self.server.scheduler.save_jobs(jobs)
        self._send_json({'ok': True, 'count': count})
      except Exception as exc:
        self._send_json({'ok': False, 'error': str(exc)}, status=400)
      return

    if path == '/api/clients':
      try:
        payload = self._read_json_body()
        name = (payload.get('name') or '').strip()
        url = normalize_url(payload.get('url'))
        if not name or not url:
          self._send_json({'error': 'name and url are required'}, status=400)
          return
        clients = load_clients()
        client = {'id': uuid.uuid4().hex[:8], 'name': name, 'url': url}
        clients.append(client)
        save_clients(clients)
        self._send_json({'client': client, 'clients': clients}, status=201)
      except Exception as exc:
        self._send_json({'error': str(exc)}, status=400)
      return

    parts = [p for p in path.split('/') if p]
    if len(parts) == 4 and parts[0] == 'api' and parts[1] == 'clients' and parts[3] in ('lights', 'reload'):
      client_id = parts[2]
      action = parts[3]
      client = find_client(client_id)
      if client is None:
        self._send_json({'error': 'Client not found'}, status=404)
        return
      try:
        if action == 'reload':
          res = requests.post(client['url'] + '/lights/reload', timeout=5)
        else:
          config = self._read_json_body()
          res = requests.post(client['url'] + '/lights', json=config, timeout=5)
        self._send_json(res.json(), status=res.status_code)
      except Exception as exc:
        self._send_json({'error': str(exc)}, status=502)
      return

    self._send_json({'error': 'Not Found'}, status=404)

  def do_DELETE(self):
    path = urlparse(self.path).path
    parts = [p for p in path.split('/') if p]
    if len(parts) == 3 and parts[0] == 'api' and parts[1] == 'clients':
      client_id = parts[2]
      clients = [c for c in load_clients() if c.get('id') != client_id]
      save_clients(clients)
      self._send_json({'clients': clients})
      return

    self._send_json({'error': 'Not Found'}, status=404)


def main():
  port = int(os.environ.get('PORT', '5000'))
  scheduler = CronScheduler(SCHEDULE_FILE, load_clients)
  scheduler.start()
  server = ThreadingHTTPServer(('0.0.0.0', port), LightsUIHandler)
  server.scheduler = scheduler
  print(f'Lights UI running on http://localhost:{port}')
  server.serve_forever()


if __name__ == '__main__':
  main()
