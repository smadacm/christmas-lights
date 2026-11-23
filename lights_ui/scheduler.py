from datetime import datetime
import json
from pathlib import Path
import threading
import time

import requests


def _match_field(expr, value, min_val, max_val, is_weekday=False):
  for part in expr.split(','):
    part = part.strip()
    if not part:
      continue

    step = 1
    if '/' in part:
      part, step_str = part.split('/', 1)
      step = max(1, int(step_str))

    if part == '*':
      start, end = min_val, max_val
    elif '-' in part:
      start_s, end_s = part.split('-', 1)
      start, end = int(start_s), int(end_s)
    else:
      n = int(part)
      if is_weekday and n == 7:
        n = 0
      if value == n:
        return True
      continue

    if is_weekday:
      if start == 7:
        start = 0
      if end == 7:
        end = 6

    if start <= value <= end and (value - start) % step == 0:
      return True

  return False


def cron_matches(cron_expr, dt):
  """Check if a 5-field cron expression matches a datetime object."""
  fields = (cron_expr or '').strip().split()
  if len(fields) != 5:
    return False

  minute_f, hour_f, day_f, month_f, wday_f = fields
  # Python weekday(): 0=Mon..6=Sun -> cron: 0=Sun..6=Sat
  cron_wday = (dt.weekday() + 1) % 7

  return (
    _match_field(minute_f, dt.minute, 0, 59)
    and _match_field(hour_f, dt.hour, 0, 23)
    and _match_field(day_f, dt.day, 1, 31)
    and _match_field(month_f, dt.month, 1, 12)
    and _match_field(wday_f, cron_wday, 0, 6, is_weekday=True)
  )


class CronScheduler:
  """Background cron scheduler that pushes configurations to remote lights_worker clients."""

  def __init__(self, schedule_path, clients_loader):
    self.schedule_path = Path(schedule_path)
    self.clients_loader = clients_loader
    self._last_minute = None
    self._stop_event = threading.Event()
    self._thread = None

  def load_jobs(self):
    if not self.schedule_path.exists():
      return []
    try:
      with self.schedule_path.open() as fd:
        data = json.load(fd)
      jobs = data.get('jobs', [])
      return jobs if isinstance(jobs, list) else []
    except (OSError, ValueError):
      return []

  def save_jobs(self, jobs):
    if not isinstance(jobs, list):
      raise ValueError('jobs must be a list')
    with self.schedule_path.open('w') as fd:
      json.dump({'jobs': jobs}, fd, indent=2)
    return len(jobs)

  def _resolve_targets(self, client_id):
    clients = self.clients_loader()
    if not client_id or client_id == 'all':
      return clients
    return [c for c in clients if c.get('id') == client_id]

  def execute_job(self, job):
    config = job.get('config')
    if not isinstance(config, dict):
      return
    targets = self._resolve_targets(job.get('client_id', 'all'))
    for client in targets:
      url = (client.get('url') or '').rstrip('/') + '/lights'
      try:
        res = requests.post(url, json=config, timeout=5)
        print(f"[Scheduler] '{job.get('name')}' -> {client.get('name')} ({res.status_code})")
      except Exception as exc:
        print(f"[Scheduler] '{job.get('name')}' -> {client.get('name')} failed: {exc}")

  def check_and_run(self):
    now = datetime.now()
    minute_key = (now.year, now.month, now.day, now.hour, now.minute)
    if minute_key == self._last_minute:
      return
    self._last_minute = minute_key

    for job in self.load_jobs():
      if not job.get('enabled', True):
        continue
      if cron_matches(job.get('cron', ''), now):
        self.execute_job(job)

  def start(self):
    if self._thread is not None and self._thread.is_alive():
      return
    self._thread = threading.Thread(target=self._loop, daemon=True)
    self._thread.start()

  def _loop(self):
    while not self._stop_event.is_set():
      try:
        self.check_and_run()
      except Exception as exc:
        print('[Scheduler] Loop error:', exc)
      self._stop_event.wait(10)
