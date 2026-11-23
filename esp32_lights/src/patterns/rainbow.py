from patterns.base import Action


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


class Rainbow(Action):
  name = 'rainbow'

  def setup(self):
    self.offset = 0

  def configure(self, step=8, sleep_ms=50, **kwargs):
    self.step = max(1, min(255, int(step)))
    self.sleep_ms = max(1, int(sleep_ms))

  def get_params(self):
    return {
      'step': self.step,
      'sleep_ms': self.sleep_ms,
    }

  def apply(self, pixels):
    n = self.n
    offset = self.offset
    for i in range(n):
      pixels[i] = _wheel((i * 256 // n + offset) & 255)
    self.offset = (offset + self.step) & 255
    return pixels
