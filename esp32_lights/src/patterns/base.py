import asyncio
import gc

# LEDs use GRB color order: (G, R, B)
RED = (0, 255, 0)
GREEN = (255, 0, 0)
WHITE = (255, 255, 255)
GOLD = (180, 255, 0)
OFF = (0, 0, 0)


class Pattern:
  """Base class for frame-based LED patterns."""

  name = None
  path = None
  sleep_ms = 50
  loop = True

  def __init__(self, np, controller=None):
    self._np = np
    self._controller = controller
    self.n = len(np)
    self.pixels = [(0, 0, 0)] * self.n
    self._buf = getattr(np, 'buf', None)
    self._bpp = getattr(np, 'bpp', 3)
    order = getattr(np, 'ORDER', (1, 0, 2, 3))
    self._o0 = order[0]
    self._o1 = order[1]
    self._o2 = order[2]
    self._action_pos = 0
    self.setup()

  def setup(self):
    """Initialize per-run pattern state."""
    pass

  def cut_color(self, color):
    brightness = self._controller.get_mod('brightness') if self._controller is not None else None
    scale = brightness.get_global_scale() if brightness is not None else 128
    return (
      (color[0] * scale) >> 8,
      (color[1] * scale) >> 8,
      (color[2] * scale) >> 8,
    )

  def write(self):
    n = self.n
    pixels = self.pixels
    ctrl = self._controller
    b_scale = 256
    mods = ctrl.mods.values() if ctrl is not None else ()

    scale_spec = None
    for mod in mods:
      if mod.is_active():
        g_scale = mod.get_global_scale()
        if g_scale is not None:
          b_scale = (b_scale * g_scale) >> 8
        if scale_spec is None:
          spec = mod.get_scale_table()
          if spec is not None:
            scale_spec = spec

    buf = self._buf
    np = self._np
    o0 = self._o0
    o1 = self._o1
    o2 = self._o2

    if buf is not None and self._bpp == 3:
      if scale_spec is not None:
        table, width, offset = scale_spec
        for i in range(n):
          c = pixels[i]
          scale = (table[(i - offset) % width] * b_scale) >> 8
          j = i * 3
          buf[j + o0] = (c[0] * scale) >> 8
          buf[j + o1] = (c[1] * scale) >> 8
          buf[j + o2] = (c[2] * scale) >> 8
      else:
        for i in range(n):
          c = pixels[i]
          j = i * 3
          buf[j + o0] = (c[0] * b_scale) >> 8
          buf[j + o1] = (c[1] * b_scale) >> 8
          buf[j + o2] = (c[2] * b_scale) >> 8
      target_buf = buf
    else:
      target_buf = None
      if scale_spec is not None:
        table, width, offset = scale_spec
        for i in range(n):
          c = pixels[i]
          scale = (table[(i - offset) % width] * b_scale) >> 8
          np[i] = ((c[0] * scale) >> 8, (c[1] * scale) >> 8, (c[2] * scale) >> 8)
      else:
        for i in range(n):
          c = pixels[i]
          np[i] = ((c[0] * b_scale) >> 8, (c[1] * b_scale) >> 8, (c[2] * b_scale) >> 8)

    for mod in mods:
      if mod.is_active():
        mod.post_write(target_buf, np, n, b_scale, o0, o1, o2)

    gc.disable()
    np.write()
    gc.enable()

  def fill(self, color):
    for i in range(self.n):
      self.pixels[i] = color

  def clear(self):
    self.fill((0, 0, 0))

  def wipe(self, color, pos=None, edge=0, step=1):
    """Fill pixels up to pos with color, with an optional leading-edge ramp.

    Returns (next_pos, done). If pos is None, uses and updates self._action_pos.
    """
    use_internal = pos is None
    if use_internal:
      pos = self._action_pos

    n = self.n
    pixels = self.pixels
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

    if use_internal:
      self._action_pos = next_pos
    return next_pos, done

  def shoot(self, color, pos=None, width=5, ramp=True, step=1, clear_bg=True, reverse=False):
    """Move a pulse of `width` pixels across the strip by `step` pixels per frame.

    Returns (next_pos, done). If pos is None, uses and updates self._action_pos.
    """
    use_internal = pos is None
    if use_internal:
      pos = self._action_pos if not reverse else self.n - 1 - self._action_pos

    n = self.n
    pixels = self.pixels
    width = max(1, int(width))
    step = max(1, int(step))

    if clear_bg:
      self.clear()

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

    if use_internal:
      self._action_pos = (n - 1 - next_pos) if reverse else next_pos
    return next_pos, done

  def render_frame(self):
    """Render a single frame into self.pixels. Return False to stop."""
    raise NotImplementedError

  def get_sleep_ms(self):
    modifier = self._controller.sleep_modifier if self._controller is not None else 1.0
    return max(10, int(round(self.sleep_ms * modifier)))

  async def run(self):
    while True:
      keep_going = self.render_frame()
      if self._controller is not None:
        self._controller.step_modifications()
      self.write()
      await asyncio.sleep_ms(0)
      if not self.loop or keep_going is False:
        break
      await asyncio.sleep_ms(self.get_sleep_ms())
