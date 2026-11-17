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
    self.dirs = [0, 0, 0]
    self.iter = RAINBOW_ITER if RAINBOW_ITER else -1

  def render_frame(self):
    if self.iter == 0:
      return False

    this_color = self.colors.pop()
    this_color[0] = self.colors[0][0]
    this_color[1] = self.colors[0][1]
    this_color[2] = self.colors[0][2]
    self.dirs[0] = self.gd
    self.dirs[1] = self.rd
    self.dirs[2] = self.bd

    for i, c in enumerate(this_color):
      if self.dirs[i] == 1:
        c += RAINBOW_STEP
      elif self.dirs[i] == -1:
        c -= RAINBOW_STEP
      if c > 255:
        c = 255
      elif c < 0:
        c = 0
      this_color[i] = c

    self.colors.insert(0, this_color)

    if this_color[0] in (0, 255) and this_color[1] in (0, 255) and this_color[2] in (0, 255):
      self.gd, self.rd, self.bd = RAINBOW_DIR_MAP.get(
        tuple(this_color), (self.gd, self.rd, self.bd)
      )

    if DEBUG:
      print('this_color', this_color)
      print('rd,gd,bd', self.rd, self.gd, self.bd)

    for i in range(self.n):
      self.pixels[i] = self.colors[i]

    if self.iter > 0:
      self.iter -= 1

    return self.iter != 0
