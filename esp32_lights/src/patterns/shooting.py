from patterns.base import Action, parse_hex_palette

DEFAULT_PALETTE = ['#ff0000', '#00ff00']


class Shooting(Action):
  """Shooting comets with fading tails for each color in the palette."""

  name = 'shooting'

  def setup(self):
    self._state = [[0, 0, 0] for _ in range(self.n)]

  def configure(self, palette=None, sleep_ms=25, **kwargs):
    self.palette_hex, self.palette = parse_hex_palette(palette, DEFAULT_PALETTE)
    self.sleep_ms = max(1, int(sleep_ms))
    num = len(self.palette)
    self.positions = [(i * self.n) // num for i in range(num)]

  def get_params(self):
    return {
      'palette': list(self.palette_hex),
      'sleep_ms': self.sleep_ms,
    }

  def apply(self, pixels):
    state = self._state
    n = self.n
    for i in range(n):
      p = state[i]
      p[0] = (p[0] * 3) >> 2
      p[1] = (p[1] * 3) >> 2
      p[2] = (p[2] * 3) >> 2

    for idx, color in enumerate(self.palette):
      pos = self.positions[idx]
      p = state[pos]
      p[0], p[1], p[2] = color[0], color[1], color[2]
      self.positions[idx] = (pos + 1) % n

    for i in range(n):
      p = state[i]
      pixels[i] = (p[0], p[1], p[2])
    return pixels
