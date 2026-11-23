# LEDs use GRB color order: (G, R, B)
RED = (0, 255, 0)
GREEN = (255, 0, 0)
WHITE = (255, 255, 255)
GOLD = (180, 255, 0)
OFF = (0, 0, 0)


def hex_to_grb(hex_str):
  """Convert a #rrggbb hex string to a (G, R, B) tuple."""
  if not isinstance(hex_str, str):
    raise ValueError('Palette colors must be hex strings: {}'.format(hex_str))
  s = hex_str.strip().lstrip('#')
  if len(s) != 6:
    raise ValueError('Invalid hex color: {}'.format(hex_str))
  r = int(s[0:2], 16)
  g = int(s[2:4], 16)
  b = int(s[4:6], 16)
  return (g, r, b)


def parse_hex_palette(palette, default_hex):
  """Parse a list of #rrggbb hex strings into (normalized_hex_list, grb_tuple)."""
  raw = palette if isinstance(palette, (list, tuple)) and len(palette) > 0 else default_hex
  hex_list = []
  grb_list = []
  for item in raw:
    grb = hex_to_grb(item)
    hex_list.append('#' + item.strip().lstrip('#').lower())
    grb_list.append(grb)
  return hex_list, tuple(grb_list)


class Action:
  """Base class for all frame pipeline actions (patterns and modifications)."""

  name = None
  sleep_ms = 0
  loop = True

  def __init__(self, n, **params):
    self.n = n
    self.configure(**params)
    self.setup()

  def setup(self):
    """Initialize per-run state."""
    pass

  def configure(self, **params):
    """Update action parameters."""
    pass

  def get_params(self):
    """Return serializable parameters for this action."""
    return {}

  def to_dict(self):
    return {
      'name': self.name,
      'params': self.get_params(),
    }

  def apply(self, pixels):
    """Transform or populate pixels and return the resulting pixel list."""
    return pixels

  def fill(self, pixels, color):
    for i in range(self.n):
      pixels[i] = color

  def clear(self, pixels):
    self.fill(pixels, OFF)

  def wipe(self, pixels, color, pos, edge=0, step=1):
    """Fill pixels up to pos with color, with an optional leading-edge ramp."""
    n = self.n
    step = max(1, int(step))
    edge = max(0, int(edge))

    solid_end = min(n, pos - edge + 1) if edge > 0 else min(n, pos + step)
    for i in range(max(0, solid_end)):
      pixels[i] = color

    if edge > 0:
      for k in range(edge):
        idx = pos - k
        if 0 <= idx < n:
          scale = ((k + 1) * 256) // (edge + 1)
          pixels[idx] = (
            (color[0] * scale) >> 8,
            (color[1] * scale) >> 8,
            (color[2] * scale) >> 8,
          )

    next_pos = pos + step
    done = (pos - edge) >= n if edge > 0 else next_pos >= n
    if done:
      next_pos = 0
    return next_pos, done

  def shoot(self, pixels, color, pos, width=5, ramp=True, step=1, clear_bg=True, reverse=False):
    """Move a pulse of `width` pixels across the strip by `step` pixels per frame."""
    n = self.n
    width = max(1, int(width))
    step = max(1, int(step))

    if clear_bg:
      self.clear(pixels)

    for k in range(width):
      idx = pos + k if reverse else pos - k
      if 0 <= idx < n:
        if ramp and width > 1:
          scale = ((width - k) * 256) // width
          pixels[idx] = (
            (color[0] * scale) >> 8,
            (color[1] * scale) >> 8,
            (color[2] * scale) >> 8,
          )
        else:
          pixels[idx] = color

    if reverse:
      next_pos = pos - step
      done = next_pos < -width
      if done:
        next_pos = n - 1
    else:
      next_pos = pos + step
      done = next_pos >= n + width
      if done:
        next_pos = 0
    return next_pos, done
