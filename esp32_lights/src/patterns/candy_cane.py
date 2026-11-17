from patterns.base import Pattern, RED, WHITE


class CandyCane(Pattern):
  """Scrolling red and white candy cane stripes."""

  name = 'candy_cane'
  path = '/candy_cane'
  sleep_ms = 120

  def setup(self):
    stripe_len = 4
    self.period = stripe_len * 2
    self.offset = 0
    self.frames = [
      [
        RED if ((i + offset) % self.period) < stripe_len else WHITE
        for i in range(self.n)
      ]
      for offset in range(self.period)
    ]

  def render_frame(self):
    self.pixels = self.frames[self.offset]
    self.offset = (self.offset + 1) % self.period
