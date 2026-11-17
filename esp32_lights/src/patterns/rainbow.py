from patterns.base import Pattern

DEBUG = False
RAINBOW_STEP = 5
RAINBOW_SLEEP = 20
RAINBOW_ITER = 0

RAINBOW_DIR_MAP = {
  (255, 0, 0): [0, 1, 0],
  (255, 255, 0): [-1, 0, 0],
  (0, 255, 0): [0, 0, 1],
  (0, 255, 255): [0, -1, 0],
  (0, 0, 255): [1, 0, 0],
  (255, 0, 255): [0, 0, -1],
}


class Rainbow(Pattern):
  name = 'rainbow'
  path = '/rainbow'
  sleep_ms = RAINBOW_SLEEP

  def setup(self):
    self.rd = 1
    self.gd = 0
    self.bd = 0
    self.colors = [list(self.pixels[i]) for i in range(self.n)]
    self.head = 0
    self.iter = RAINBOW_ITER if RAINBOW_ITER else -1

  def render_frame(self):
    if self.iter == 0:
      return False

    n = self.n
    colors = self.colors
    prev = colors[self.head]
    self.head = (self.head - 1) % n
    this_color = colors[self.head]

    c0 = prev[0] + (RAINBOW_STEP if self.gd == 1 else (-RAINBOW_STEP if self.gd == -1 else 0))
    c1 = prev[1] + (RAINBOW_STEP if self.rd == 1 else (-RAINBOW_STEP if self.rd == -1 else 0))
    c2 = prev[2] + (RAINBOW_STEP if self.bd == 1 else (-RAINBOW_STEP if self.bd == -1 else 0))

    if c0 > 255:
      c0 = 255
    elif c0 < 0:
      c0 = 0
    if c1 > 255:
      c1 = 255
    elif c1 < 0:
      c1 = 0
    if c2 > 255:
      c2 = 255
    elif c2 < 0:
      c2 = 0

    this_color[0] = c0
    this_color[1] = c1
    this_color[2] = c2

    if (c0 == 0 or c0 == 255) and (c1 == 0 or c1 == 255) and (c2 == 0 or c2 == 255):
      self.gd, self.rd, self.bd = RAINBOW_DIR_MAP.get(
        (c0, c1, c2), (self.gd, self.rd, self.bd)
      )

    if DEBUG:
      print('this_color', this_color)
      print('rd,gd,bd', self.rd, self.gd, self.bd)

    pixels = self.pixels
    idx = self.head
    for i in range(n):
      pixels[i] = colors[idx]
      idx += 1
      if idx == n:
        idx = 0

    if self.iter > 0:
      self.iter -= 1

    return self.iter != 0
