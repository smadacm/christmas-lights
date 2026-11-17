from patterns.base import GREEN, Pattern, RED, WHITE


class ChristmasChase(Pattern):
  """Red, green, and white chasing pattern."""

  name = 'christmas_chase'
  path = '/christmas_chase'
  sleep_ms = 180

  def setup(self):
    self.palette = (RED, GREEN, WHITE)
    self.offset = 0

  def render_frame(self):
    palette_len = len(self.palette)
    for i in range(self.n):
      self.pixels[i] = self.palette[(i + self.offset) % palette_len]
    self.offset = (self.offset + 1) % palette_len
