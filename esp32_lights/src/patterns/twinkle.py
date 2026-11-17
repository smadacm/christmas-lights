import random

from patterns.base import GOLD, GREEN, Pattern, RED, WHITE


class Twinkle(Pattern):
  """Gentle festive twinkle."""

  name = 'twinkle'
  path = '/twinkle'
  spawn_count = 3
  fade_step = 16
  sleep_ms = 40

  def setup(self):
    self.pixels = [[0, 0, 0] for _ in range(self.n)]
    self.palette = (RED, GREEN, WHITE, GOLD)

  def render_frame(self):
    for i in range(self.n):
      r, g, b = self.pixels[i]
      self.pixels[i][0] = r - self.fade_step if r > self.fade_step else 0
      self.pixels[i][1] = g - self.fade_step if g > self.fade_step else 0
      self.pixels[i][2] = b - self.fade_step if b > self.fade_step else 0

    for _ in range(self.spawn_count):
      idx = random.randint(0, self.n - 1)
      color = self.palette[random.randint(0, len(self.palette) - 1)]
      self.pixels[idx] = [color[0], color[1], color[2]]
