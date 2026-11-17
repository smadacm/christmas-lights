import random


class TwinkleMod:
  """Overlays non-persistent white sparkles onto any pattern frame."""

  def __init__(self, enabled=False, count=5):
    self.enabled = enabled
    self.count = max(1, int(count))
    self.active_indices = set()

  def step(self, n):
    self.active_indices.clear()
    if not self.enabled or n <= 0:
      return
    target = min(self.count, n)
    for _ in range(target):
      self.active_indices.add(random.randint(0, n - 1))

  def apply(self, index, color):
    if self.enabled and index in self.active_indices:
      return (255, 255, 255)
    return color


class WaveMod:
  """Applies a moving brightness wave (forward or reverse) across the strip."""

  def __init__(self, direction=0, min_brightness=20, max_brightness=100, width=20):
    self.direction = direction  # 0=off, 1=forward, -1=reverse
    self.min_brightness = max(0, min(100, int(min_brightness)))
    self.max_brightness = max(0, min(100, int(max_brightness)))
    self.width = max(2, int(width))
    self.offset = 0

  def step(self, n):
    if self.direction != 0:
      self.offset = (self.offset + self.direction) % self.width

  def apply(self, index, color):
    if self.direction == 0:
      return color

    pos = (index - self.offset) % self.width
    half = self.width / 2.0
    if pos <= half:
      ratio = pos / half
    else:
      ratio = (self.width - pos) / half

    scale = int(self.min_brightness + (self.max_brightness - self.min_brightness) * ratio)
    return (
      color[0] * scale // 100,
      color[1] * scale // 100,
      color[2] * scale // 100,
    )
