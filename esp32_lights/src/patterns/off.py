from patterns.base import Action


class Off(Action):
  name = 'off'
  loop = False

  def apply(self, pixels):
    self.clear(pixels)
    return pixels
