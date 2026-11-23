import random

from patterns.base import Action, parse_hex_palette

DEFAULT_PALETTE = ['#ff0000', '#00ff00', '#ffffff', '#ffb400']


class Twinkle(Action):
  """Gentle festive twinkle."""

  name = 'twinkle'

  def setup(self):
    self._state = [[0, 0, 0] for _ in range(self.n)]

  def configure(self, spawn_count=3, fade_step=16, sleep_ms=40, palette=None, **kwargs):
    self.spawn_count = max(1, min(self.n, int(spawn_count)))
    self.fade_step = max(1, min(255, int(fade_step)))
    self.sleep_ms = max(1, int(sleep_ms))
    self.palette_hex, self.palette = parse_hex_palette(palette, DEFAULT_PALETTE)

  def get_params(self):
    return {
      'spawn_count': self.spawn_count,
      'fade_step': self.fade_step,
      'sleep_ms': self.sleep_ms,
      'palette': list(self.palette_hex),
    }

  def apply(self, pixels):
    state = self._state
    fade_step = self.fade_step
    for i in range(self.n):
      p = state[i]
      p[0] = p[0] - fade_step if p[0] > fade_step else 0
      p[1] = p[1] - fade_step if p[1] > fade_step else 0
      p[2] = p[2] - fade_step if p[2] > fade_step else 0

    for _ in range(self.spawn_count):
      idx = random.randint(0, self.n - 1)
      color = self.palette[random.randint(0, len(self.palette) - 1)]
      state[idx] = [color[0], color[1], color[2]]

    for i in range(self.n):
      p = state[i]
      pixels[i] = (p[0], p[1], p[2])
    return pixels
