from patterns.base import GREEN, Pattern, RED, WHITE


class ChristmasChase(Pattern):
  """Red, green, and white chasing pattern."""

  name = 'christmas_chase'
  path = '/christmas_chase'
  sleep_ms = 180

  def setup(self):
    self.palette = (RED, GREEN, WHITE)
    self.period = len(self.palette)
    self.offset = 0

  def render_frame(self):
    pixels = self.pixels
    palette = self.palette
    period = self.period
    offset = self.offset
    for i in range(self.n):
      pixels[i] = palette[(i + offset) % period]
    self.offset = (offset + 1) % period
