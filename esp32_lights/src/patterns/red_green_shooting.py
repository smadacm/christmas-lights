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
    self.tail_decay = 0.75

  def render_frame(self):
    for i in range(self.n):
      self.pixels[i][0] = int(self.pixels[i][0] * self.tail_decay)
      self.pixels[i][1] = int(self.pixels[i][1] * self.tail_decay)
      self.pixels[i][2] = int(self.pixels[i][2] * self.tail_decay)

    self.pixels[self.pos_red] = [RED[0], RED[1], RED[2]]
    self.pixels[self.pos_green] = [GREEN[0], GREEN[1], GREEN[2]]

    self.pos_red = (self.pos_red + 1) % self.n
    self.pos_green = (self.pos_green + 1) % self.n
