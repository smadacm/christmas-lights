from patterns.base import Action, parse_hex_palette

DEFAULT_PALETTE = ['#ff0000', '#00ff00']


class WipeShoot(Action):
  """Wipes one color, shoots the next color n times over it, then advances."""

  name = 'wipe_shoot'

  def setup(self):
    self.idx = 0
    self.stage = 'wipe'
    self.pos = 0
    self.shoots_left = self.shoot_count

  def configure(
    self,
    palette=None,
    shoot_count=3,
    edge=6,
    wipe_step=2,
    shoot_width=10,
    shoot_step=3,
    sleep_ms=15,
    **kwargs
  ):
    self.palette_hex, self.palette = parse_hex_palette(palette, DEFAULT_PALETTE)
    self.shoot_count = max(1, int(shoot_count))
    self.edge = max(0, int(edge))
    self.wipe_step = max(1, int(wipe_step))
    self.shoot_width = max(1, int(shoot_width))
    self.shoot_step = max(1, int(shoot_step))
    self.sleep_ms = max(1, int(sleep_ms))

  def get_params(self):
    return {
      'palette': list(self.palette_hex),
      'shoot_count': self.shoot_count,
      'edge': self.edge,
      'wipe_step': self.wipe_step,
      'shoot_width': self.shoot_width,
      'shoot_step': self.shoot_step,
      'sleep_ms': self.sleep_ms,
    }

  def apply(self, pixels):
    num = len(self.palette)
    wipe_color = self.palette[self.idx % num]
    shoot_color = self.palette[(self.idx + 1) % num]
    prev_color = self.palette[(self.idx - 1) % num]

    if self.stage == 'wipe':
      self.fill(pixels, prev_color)
      self.pos, done = self.wipe(pixels, wipe_color, pos=self.pos, edge=self.edge, step=self.wipe_step)
      if done:
        self.stage = 'shoot'
        self.pos = 0
        self.shoots_left = self.shoot_count
    else:
      self.fill(pixels, wipe_color)
      self.pos, done = self.shoot(
        pixels,
        shoot_color,
        pos=self.pos,
        width=self.shoot_width,
        ramp=True,
        step=self.shoot_step,
        clear_bg=False,
      )
      if done:
        self.shoots_left -= 1
        if self.shoots_left <= 0:
          self.idx = (self.idx + 1) % num
          self.stage = 'wipe'
          self.pos = 0
    return pixels
