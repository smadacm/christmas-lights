import random


class Modification:
  """Base class for pattern post-processing modifications."""

  name = None

  def __init__(self, enabled=False):
    self.enabled = bool(enabled)

  def is_active(self):
    return self.enabled

  def step(self, n):
    """Advance modification state once per frame."""
    pass

  def configure(self, **kwargs):
    """Update modification parameters."""
    if 'enabled' in kwargs and kwargs['enabled'] is not None:
      self.enabled = bool(kwargs['enabled'])

  def to_dict(self):
    """Serialize modification state for config persistence."""
    return {'enabled': self.enabled}

  def load_dict(self, data):
    """Restore modification state from config data."""
    if isinstance(data, dict):
      self.configure(**data)

  def get_global_scale(self):
    """Return a 0..256 global brightness multiplier if this mod scales all LEDs, else None."""
    return None

  def get_scale_table(self):
    """Return (table, width, offset) if this mod scales pixel brightness, else None."""
    return None

  def post_write(self, buf, np, n, b_scale, o0, o1, o2):
    """Apply overlay writes directly to buf or np after the base pixel loop."""
    pass


class BrightnessMod(Modification):
  """Scales overall LED brightness (0-100%)."""

  name = 'brightness'

  def __init__(self, level=50):
    super().__init__(enabled=True)
    self.level = max(0, min(100, int(level)))

  def configure(self, level=None, delta=None, **kwargs):
    if delta is not None:
      self.level = max(0, min(100, self.level + int(delta)))
    if level is not None:
      self.level = max(0, min(100, int(level)))

  def to_dict(self):
    return {'level': self.level}

  def get_global_scale(self):
    return (self.level * 256) // 100


class TwinkleMod(Modification):
  """Overlays non-persistent white sparkles onto any pattern frame."""

  name = 'twinkle'

  def __init__(self, enabled=False, count=5, speed=1):
    super().__init__(enabled=enabled)
    self.count = max(1, int(count))
    self.speed = max(1, int(speed))
    self._frame = 0
    self.active_indices = set()

  def configure(self, enabled=None, count=None, speed=None, n=1000):
    if enabled is not None:
      self.enabled = bool(enabled)
      self._frame = 0
    if count is not None:
      self.count = max(1, min(n, int(count)))
      self._frame = 0
    if speed is not None:
      self.speed = max(1, int(speed))
      self._frame = 0

  def to_dict(self):
    return {
      'enabled': self.enabled,
      'count': self.count,
      'speed': self.speed,
    }

  def step(self, n):
    if not self.enabled or n <= 0:
      self.active_indices.clear()
      self._frame = 0
      return
    if self._frame == 0 or not self.active_indices:
      self.active_indices.clear()
      target = min(self.count, n)
      for _ in range(target):
        self.active_indices.add(random.randint(0, n - 1))
    self._frame = (self._frame + 1) % self.speed

  def post_write(self, buf, np, n, b_scale, o0, o1, o2):
    if not self.enabled or not self.active_indices:
      return
    w = (255 * b_scale) >> 8
    if buf is not None:
      for idx in self.active_indices:
        if 0 <= idx < n:
          j = idx * 3
          buf[j + o0] = w
          buf[j + o1] = w
          buf[j + o2] = w
    else:
      white = (w, w, w)
      for idx in self.active_indices:
        if 0 <= idx < n:
          np[idx] = white


class WaveMod(Modification):
  """Applies a moving brightness wave (forward or reverse) across the strip."""

  name = 'wave'

  def __init__(self, direction=0, min_brightness=20, max_brightness=100, width=20):
    super().__init__(enabled=(direction != 0))
    self.direction = int(direction)  # 0=off, 1=forward, -1=reverse
    self.min_brightness = max(0, min(100, int(min_brightness)))
    self.max_brightness = max(0, min(100, int(max_brightness)))
    self.width = max(2, int(width))
    self.offset = 0
    self.table = []
    self.rebuild_table()

  def is_active(self):
    return self.direction != 0

  def configure(self, direction=None, min_brightness=None, max_brightness=None, width=None, **kwargs):
    if direction is not None:
      self.direction = int(direction)
      self.enabled = self.direction != 0
    if min_brightness is not None:
      self.min_brightness = max(0, min(100, int(min_brightness)))
    if max_brightness is not None:
      self.max_brightness = max(0, min(100, int(max_brightness)))
    if self.min_brightness > self.max_brightness:
      self.min_brightness = self.max_brightness
    if width is not None:
      self.width = max(2, int(width))
    self.rebuild_table()

  def to_dict(self):
    return {
      'direction': self.direction,
      'min_brightness': self.min_brightness,
      'max_brightness': self.max_brightness,
      'width': self.width,
    }

  def rebuild_table(self):
    half = self.width / 2.0
    table = []
    for pos in range(self.width):
      if pos <= half:
        ratio = pos / half
      else:
        ratio = (self.width - pos) / half
      pct = self.min_brightness + (self.max_brightness - self.min_brightness) * ratio
      table.append(int(pct * 256 / 100))
    self.table = table

  def step(self, n):
    if self.direction != 0:
      self.offset = (self.offset + self.direction) % self.width

  def get_scale_table(self):
    if self.direction == 0:
      return None
    return (self.table, self.width, self.offset)
