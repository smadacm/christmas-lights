from patterns.base import Action, parse_hex_palette

DEFAULT_PALETTE = ['#ff0000', '#00ff00']


class Wipe(Action):
  """Sequentially wipes through a palette of colors across the strip."""

  name = 'wipe'

  def setup(self):
    self.color_idx = 0
    self.pos = 0
    self.pause = 0

  def configure(self, palette=None, edge=6, step=1, pause_frames=13, sleep_ms=15, **kwargs):
    self.palette_hex, self.palette = parse_hex_palette(palette, DEFAULT_PALETTE)
    self.edge = max(0, int(edge))
    self.step = max(1, int(step))
    self.pause_frames = max(0, int(pause_frames))
    self.sleep_ms = max(1, int(sleep_ms))

  def get_params(self):
    return {
      'palette': list(self.palette_hex),
      'edge': self.edge,
      'step': self.step,
      'pause_frames': self.pause_frames,
      'sleep_ms': self.sleep_ms,
    }

  def apply(self, pixels):
    num_colors = len(self.palette)
    prev_color = self.palette[(self.color_idx - 1) % num_colors]
    self.fill(pixels, prev_color)

    if self.pause > 0:
      self.pause -= 1
      return pixels

    self.pos, done = self.wipe(
      pixels,
      self.palette[self.color_idx],
      pos=self.pos,
      edge=self.edge,
      step=self.step,
    )
    if done:
      self.color_idx = (self.color_idx + 1) % num_colors
      self.pause = self.pause_frames
    return pixels
