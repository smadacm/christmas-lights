from patterns.base import Pattern, RED, WHITE


class CandyCane(Pattern):
  """Scrolling red and white candy cane stripes."""

  name = 'candy_cane'
  path = '/candy_cane'
  sleep_ms = 120

  def setup(self):
    self.stripe_len = 4
    self.period = self.stripe_len * 2
    self.offset = 0

  def render_frame(self):
    pixels = self.pixels
    stripe_len = self.stripe_len
    period = self.period
    offset = self.offset
    for i in range(self.n):
      pixels[i] = RED if ((i + offset) % period) < stripe_len else WHITE
    self.offset = (offset + 1) % period
