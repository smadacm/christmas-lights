from patterns.base import GREEN, Pattern, RED


class RedGreenWipe(Pattern):
  """Sequentially wipes red then green across the strip."""

  name = 'red_green_wipe'
  path = '/red_green_wipe'
  sleep_ms = 15

  def setup(self):
    self.colors = (RED, GREEN)
    self.color_idx = 0
    self.pos = 0
    self.pause_frames = 0

  def render_frame(self):
    if self.pause_frames > 0:
      self.pause_frames -= 1
      return

    self.pos, done = self.wipe(self.colors[self.color_idx], pos=self.pos, edge=6, step=1)
    if done:
      self.color_idx = (self.color_idx + 1) % len(self.colors)
      self.pause_frames = 13
