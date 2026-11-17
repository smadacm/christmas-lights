from patterns.base import GREEN, Pattern, RED


class RedGreenShooting(Pattern):
  """Shooting red and green comets with fading tails."""

  name = 'red_green_shooting'
  path = '/red_green_shooting'
  sleep_ms = 25

  def setup(self):
    self.pixels = [[0, 0, 0] for _ in range(self.n)]
    self.pos_red = 0
    self.pos_green = self.n // 2

  def render_frame(self):
    pixels = self.pixels
    for i in range(self.n):
      p = pixels[i]
      p[0] = (p[0] * 3) >> 2
      p[1] = (p[1] * 3) >> 2
      p[2] = (p[2] * 3) >> 2

    pr = pixels[self.pos_red]
    pr[0], pr[1], pr[2] = RED[0], RED[1], RED[2]

    pg = pixels[self.pos_green]
    pg[0], pg[1], pg[2] = GREEN[0], GREEN[1], GREEN[2]

    self.pos_red = (self.pos_red + 1) % self.n
    self.pos_green = (self.pos_green + 1) % self.n
