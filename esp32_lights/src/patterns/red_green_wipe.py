from patterns.base import GREEN, Pattern, RED


class RedGreenWipe(Pattern):
  """Sequentially wipes red then green across the strip."""

  name = 'red_green_wipe'
  path = '/red_green_wipe'
  sleep_ms = 15

  def setup(self):
    self.colors = (RED, GREEN)
    self.color_idx = 0
    self.pixel_idx = 0
    self.pause_frames = 0

  def render_frame(self):
    if self.pause_frames > 0:
      self.pause_frames -= 1
      return

    self.pixels[self.pixel_idx] = self.colors[self.color_idx]
    self.pixel_idx += 1

    if self.pixel_idx >= self.n:
      self.pixel_idx = 0
      self.color_idx = (self.color_idx + 1) % len(self.colors)
      self.pause_frames = 13
