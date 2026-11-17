from patterns.base import Pattern


class Basic(Pattern):
  name = 'basic'
  path = '/basic'
  loop = False

  def render_frame(self):
    for i in range(self.n):
      self.pixels[i] = (0, int((1.0 / self.n) * 200 * i), 155)
