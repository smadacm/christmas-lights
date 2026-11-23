from patterns.base import Action


class Basic(Action):
  name = 'basic'
  loop = False

  def apply(self, pixels):
    for i in range(self.n):
      pixels[i] = (0, int((1.0 / self.n) * 200 * i), 155)
    return pixels
