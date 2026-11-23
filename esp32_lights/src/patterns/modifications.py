import random

from patterns.base import Action


class BrightnessMod(Action):
  """Scales overall LED brightness (0-100%)."""

  name = 'brightness'
  loop = False

  def configure(self, level=50, **kwargs):
    self.level = max(0, min(100, int(level)))
    self._scale = (self.level * 256) // 100

  def get_params(self):
    return {'level': self.level}

  def apply(self, pixels):
    scale = self._scale
    for i in range(self.n):
      c = pixels[i]
      pixels[i] = (
        (c[0] * scale) >> 8,
        (c[1] * scale) >> 8,
        (c[2] * scale) >> 8,
      )
    return pixels


class TwinkleMod(Action):
  """Overlays non-persistent white sparkles onto the pixel pipeline."""

  name = 'twinkle_mod'
  loop = True

  def setup(self):
    self._frame = 0
    self._indices = set()

  def configure(self, count=5, speed=1, **kwargs):
    self.count = max(1, min(self.n, int(count)))
    self.speed = max(1, int(speed))
    self._frame = 0

  def get_params(self):
    return {
      'count': self.count,
      'speed': self.speed,
    }

  def apply(self, pixels):
    n = self.n
    if n <= 0:
      return pixels

    if self._frame == 0 or not self._indices:
      self._indices.clear()
      target = min(self.count, n)
      for _ in range(target):
        self._indices.add(random.randint(0, n - 1))
    self._frame = (self._frame + 1) % self.speed

    for idx in self._indices:
      if 0 <= idx < n:
        pixels[idx] = (255, 255, 255)
    return pixels


class WaveMod(Action):
  """Applies a moving brightness wave (forward or reverse) across the strip."""

  name = 'wave'
  loop = True

  def setup(self):
    self.offset = 0

  def configure(self, direction=1, min_brightness=20, max_brightness=100, width=20, **kwargs):
    self.direction = int(direction)
    self.min_brightness = max(0, min(100, int(min_brightness)))
    self.max_brightness = max(0, min(100, int(max_brightness)))
    if self.min_brightness > self.max_brightness:
      self.min_brightness = self.max_brightness
    self.width = max(2, int(width))
    self._rebuild_table()

  def get_params(self):
    return {
      'direction': self.direction,
      'min_brightness': self.min_brightness,
      'max_brightness': self.max_brightness,
      'width': self.width,
    }

  def _rebuild_table(self):
    half = self.width / 2.0
    table = []
    for pos in range(self.width):
      if pos <= half:
        ratio = pos / half
      else:
        ratio = (self.width - pos) / half
      pct = self.min_brightness + (self.max_brightness - self.min_brightness) * ratio
      table.append(int(pct * 256 / 100))
    self._table = table

  def apply(self, pixels):
    if self.direction == 0:
      return pixels

    table = self._table
    width = self.width
    offset = self.offset
    for i in range(self.n):
      c = pixels[i]
      scale = table[(i - offset) % width]
      pixels[i] = (
        (c[0] * scale) >> 8,
        (c[1] * scale) >> 8,
        (c[2] * scale) >> 8,
      )
    self.offset = (self.offset + self.direction) % width
    return pixels
