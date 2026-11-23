from patterns.base import Action, parse_hex_palette

DEFAULT_PALETTE = ['#ff0000', '#00ff00', '#ffffff']


class Chase(Action):
  """Scrolling palette chase with configurable block size and sleep."""

  name = 'chase'

  def setup(self):
    self.offset = 0

  def configure(self, palette=None, block_size=1, sleep_ms=180, **kwargs):
    self.palette_hex, self.palette = parse_hex_palette(palette, DEFAULT_PALETTE)
    self.block_size = max(1, int(block_size))
    self.sleep_ms = max(1, int(sleep_ms))
    self.period = len(self.palette) * self.block_size

  def get_params(self):
    return {
      'palette': list(self.palette_hex),
      'block_size': self.block_size,
      'sleep_ms': self.sleep_ms,
    }

  def apply(self, pixels):
    palette = self.palette
    num_colors = len(palette)
    block_size = self.block_size
    period = self.period
    offset = self.offset
    for i in range(self.n):
      color_idx = (((i + offset) % period) // block_size) % num_colors
      pixels[i] = palette[color_idx]
    self.offset = (offset + 1) % period
    return pixels
