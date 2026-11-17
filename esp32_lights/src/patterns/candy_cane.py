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
    for i in range(self.n):
      if ((i + self.offset) % self.period) < self.stripe_len:
        self.pixels[i] = RED
      else:
        self.pixels[i] = WHITE
    self.offset = (self.offset + 1) % self.period
