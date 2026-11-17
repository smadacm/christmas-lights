import asyncio
import json
import time

try:
  import ntptime
except ImportError:
  ntptime = None


def _is_eastern_dst(utc_sec):
  """Return True if utc_sec falls within US Eastern Daylight Saving Time."""
  year = time.gmtime(utc_sec)[0]

  # Second Sunday of March at 02:00 EST (07:00 UTC)
  march_1_wday = time.gmtime(time.mktime((year, 3, 1, 0, 0, 0, 0, 0)))[6]
  march_first_sun = 1 + (6 - march_1_wday) % 7
  dst_start_day = march_first_sun + 7
  dst_start_utc = time.mktime((year, 3, dst_start_day, 7, 0, 0, 0, 0))

  # First Sunday of November at 02:00 EDT (06:00 UTC)
  nov_1_wday = time.gmtime(time.mktime((year, 11, 1, 0, 0, 0, 0, 0)))[6]
  dst_end_day = 1 + (6 - nov_1_wday) % 7
  dst_end_utc = time.mktime((year, 11, dst_end_day, 6, 0, 0, 0, 0))

  return dst_start_utc <= utc_sec < dst_end_utc


def get_eastern_time():
  """Return current US Eastern time tuple (year, month, mday, hour, minute, second, cron_wday)."""
  utc_sec = time.time()
  offset = -4 * 3600 if _is_eastern_dst(utc_sec) else -5 * 3600
  tm = time.gmtime(utc_sec + offset)
  # Convert MicroPython weekday (0=Mon..6=Sun) to standard cron weekday (0=Sun..6=Sat)
  cron_wday = (tm[6] + 1) % 7
  return (tm[0], tm[1], tm[2], tm[3], tm[4], tm[5], cron_wday)


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


def cron_matches(cron_expr, tm):
  """Check if a 5-field cron expression matches (year, month, mday, hour, minute, second, cron_wday)."""
  fields = cron_expr.strip().split()
  if len(fields) != 5:
    return False

  minute_f, hour_f, day_f, month_f, wday_f = fields
  _, month, mday, hour, minute, _, cron_wday = tm

  return (
    _match_field(minute_f, minute, 0, 59)
    and _match_field(hour_f, hour, 0, 23)
    and _match_field(day_f, mday, 1, 31)
    and _match_field(month_f, month, 1, 12)
    and _match_field(wday_f, cron_wday, 0, 6, is_weekday=True)
  )


class CronScheduler:
  """Syncs RTC via NTP and runs scheduled controller actions from a JSON file."""

  def __init__(
    self,
    controller,
    schedule_path='schedule.json',
    ntp_host='pool.ntp.org',
    sync_interval_s=21600,
  ):
    self.controller = controller
    self.schedule_path = schedule_path
    self.ntp_host = ntp_host
    self.sync_interval_s = sync_interval_s
    self._last_sync = 0
    self._last_minute = None

  def sync_ntp(self):
    if ntptime is None:
      return False
    try:
      ntptime.host = self.ntp_host
      ntptime.settime()
      self._last_sync = time.time()
      print('NTP synced. Eastern time:', get_eastern_time()[:6])
      return True
    except Exception as exc:
      print('NTP sync failed:', exc)
      return False

  def load_jobs(self):
    try:
      with open(self.schedule_path) as fd:
        data = json.load(fd)
      jobs = data.get('jobs', [])
      return jobs if isinstance(jobs, list) else []
    except (OSError, ValueError):
      return []

  def save_jobs(self, jobs):
    if not isinstance(jobs, list):
      raise ValueError('jobs must be a list')
    with open(self.schedule_path, 'w') as fd:
      json.dump({'jobs': jobs}, fd)
    return len(jobs)

  def execute_action(self, action):
    action_type = action.get('type')
    if action_type == 'program':
      name = action.get('name')
      if name:
        self.controller.set_program(name)
    elif action_type == 'mod':
      name = action.get('name')
      params = action.get('params', {})
      if name and isinstance(params, dict):
        self.controller.configure_mod(name, **params)

  def check_and_run(self):
    tm = get_eastern_time()
    minute_key = tm[:5]
    if minute_key == self._last_minute:
      return
    self._last_minute = minute_key

    for job in self.load_jobs():
      if not job.get('enabled', True):
        continue
      cron_expr = job.get('cron', '')
      if cron_matches(cron_expr, tm):
        print('Running scheduled job:', job.get('name', cron_expr))
        for action in job.get('actions', []):
          self.execute_action(action)

  async def run(self):
    self.sync_ntp()
    while True:
      now = time.time()
      if self._last_sync == 0 or (now - self._last_sync) >= self.sync_interval_s:
        self.sync_ntp()

      if self._last_sync > 0:
        self.check_and_run()

      await asyncio.sleep(10)
