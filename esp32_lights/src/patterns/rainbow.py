from patterns.base import Pattern

RAINBOW_STEP = 8
RAINBOW_SLEEP = 50


def _wheel(pos):
  """Map 0..255 position to a (G, R, B) tuple with zero heap tables."""
  pos = pos & 255
  if pos < 85:
    return (pos * 3, 255 - pos * 3, 0)
  if pos < 170:
    pos -= 85
    return (255 - pos * 3, 0, pos * 3)
  pos -= 170
  return (0, pos * 3, 255 - pos * 3)


class Rainbow(Pattern):
  name = 'rainbow'
  path = '/rainbow'
  sleep_ms = RAINBOW_SLEEP

  def setup(self):
    self.offset = 0

  def render_frame(self):
    n = self.n
    pixels = self.pixels
    offset = self.offset
    for i in range(n):
      pixels[i] = _wheel((i * 256 // n + offset) & 255)
    self.offset = (offset + RAINBOW_STEP) & 255
