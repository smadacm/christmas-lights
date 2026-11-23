from patterns.base import Action


class Demo(Action):
  name = 'demo'

  def setup(self):
    self.sleep_ms = int(5000.0 / self.n)
    self.stage = 0
    self.step = 0

  def apply(self, pixels):
    n = self.n

    if self.stage == 0:
      self.clear(pixels)
      pixels[self.step % n] = (255, 255, 255)
      self.step += 1
      if self.step >= 4 * n:
        self.stage = 1
        self.step = 0
      return pixels

    if self.stage == 1:
      self.fill(pixels, (0, 0, 128))
      if (self.step // n) % 2 == 0:
        pixels[self.step % n] = (0, 0, 0)
      else:
        pixels[n - 1 - (self.step % n)] = (0, 0, 0)
      self.step += 1
      if self.step >= 4 * n:
        self.stage = 2
        self.step = 0
        self.sleep_ms = 10
      return pixels

    if self.stage == 2:
      if (self.step // 256) % 2 == 0:
        val = self.step & 0xff
      else:
        val = 255 - (self.step & 0xff)
      self.fill(pixels, (val, 0, 0))
      self.step += 8
      if self.step >= 4 * 256:
        self.stage = 3
        self.step = 0
      return pixels

    self.clear(pixels)
    self.loop = False
    return pixels
