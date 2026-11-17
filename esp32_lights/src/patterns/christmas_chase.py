from patterns.base import GREEN, Pattern, RED, WHITE


class ChristmasChase(Pattern):
  """Red, green, and white chasing pattern."""

  name = 'christmas_chase'
  path = '/christmas_chase'
  sleep_ms = 180

  def setup(self):
    palette = (RED, GREEN, WHITE)
    self.period = len(palette)
    self.offset = 0
    self.frames = [
      [palette[(i + offset) % self.period] for i in range(self.n)]
      for offset in range(self.period)
    ]

  def render_frame(self):
    self.pixels = self.frames[self.offset]
    self.offset = (self.offset + 1) % self.period
