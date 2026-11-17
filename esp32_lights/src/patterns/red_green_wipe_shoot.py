from patterns.base import GREEN, Pattern, RED


class RedGreenWipeShoot(Pattern):
  """Wipes one color, shoots the other n times over it, then swaps colors."""

  name = 'red_green_wipe_shoot'
  path = '/red_green_wipe_shoot'
  sleep_ms = 15
  shoot_count = 3

  def setup(self):
    self.colors = (RED, GREEN)
    self.idx = 0
    self.stage = 'wipe'
    self.pos = 0
    self.shoots_left = self.shoot_count

  def render_frame(self):
    wipe_color = self.colors[self.idx]
    shoot_color = self.colors[1 - self.idx]

    if self.stage == 'wipe':
      self.pos, done = self.wipe(wipe_color, pos=self.pos, edge=6, step=2)
      if done:
        self.stage = 'shoot'
        self.pos = 0
        self.shoots_left = self.shoot_count
    else:
      self.fill(wipe_color)
      self.pos, done = self.shoot(
        shoot_color,
        pos=self.pos,
        width=10,
        ramp=True,
        step=3,
        clear_bg=False,
      )
      if done:
        self.shoots_left -= 1
        if self.shoots_left <= 0:
          self.idx = 1 - self.idx
          self.stage = 'wipe'
          self.pos = 0
