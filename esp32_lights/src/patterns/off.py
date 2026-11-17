from patterns.base import Pattern


class Off(Pattern):
  name = 'off'
  path = '/off'
  loop = False

  def render_frame(self):
    self.clear()
