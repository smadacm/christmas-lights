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
    self.setup()

  def setup(self):
    """Initialize per-run pattern state."""
    pass

  def cut_color(self, color):
    brightness = self._controller.brightness if self._controller is not None else 50
    return (
      color[0] * brightness // 100,
      color[1] * brightness // 100,
      color[2] * brightness // 100,
    )

  def write(self):
    for i in range(self.n):
      color = self.pixels[i]
      if self._controller is not None:
        color = self._controller.apply_modifications(i, color)
      self._np[i] = self.cut_color(color)
    gc.disable()
    self._np.write()
    gc.enable()

  def fill(self, color):
    for i in range(self.n):
      self.pixels[i] = color

  def clear(self):
    self.fill((0, 0, 0))

  def render_frame(self):
    """Render a single frame into self.pixels. Return False to stop."""
    raise NotImplementedError

  def get_sleep_ms(self):
    modifier = self._controller.sleep_modifier if self._controller is not None else 1.0
    return max(1, int(round(self.sleep_ms * modifier)))

  async def run(self):
    while True:
      keep_going = self.render_frame()
      if self._controller is not None:
        self._controller.step_modifications()
      self.write()
      if not self.loop or keep_going is False:
        break
      await asyncio.sleep_ms(self.get_sleep_ms())
