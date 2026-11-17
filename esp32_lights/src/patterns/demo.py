from patterns.base import Pattern


class Demo(Pattern):
  name = 'demo'
  path = '/demo'

  def setup(self):
    self.sleep_ms = int(5000.0 / self.n)
    self.stage = 0
    self.step = 0

  def render_frame(self):
    n = self.n

    # Stage 0: cycle
    if self.stage == 0:
      self.clear()
      self.pixels[self.step % n] = (255, 255, 255)
      self.step += 1
      if self.step >= 4 * n:
        self.stage = 1
        self.step = 0
      return True

    # Stage 1: bounce
    if self.stage == 1:
      self.fill((0, 0, 128))
      if (self.step // n) % 2 == 0:
        self.pixels[self.step % n] = (0, 0, 0)
      else:
        self.pixels[n - 1 - (self.step % n)] = (0, 0, 0)
      self.step += 1
      if self.step >= 4 * n:
        self.stage = 2
        self.step = 0
        self.sleep_ms = 1
      return True

    # Stage 2: fade in/out
    if self.stage == 2:
      if (self.step // 256) % 2 == 0:
        val = self.step & 0xff
      else:
        val = 255 - (self.step & 0xff)
      self.fill((val, 0, 0))
      self.step += 8
      if self.step >= 4 * 256:
        self.stage = 3
        self.step = 0
      return True

    # Stage 3: clear and finish
    self.clear()
    return False
