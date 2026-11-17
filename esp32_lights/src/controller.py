import asyncio
import json

from patterns.basic import Basic
from patterns.candy_cane import CandyCane
from patterns.christmas_chase import ChristmasChase
from patterns.demo import Demo
from patterns.modifications import TwinkleMod, WaveMod
from patterns.off import Off
from patterns.rainbow import Rainbow
from patterns.red_green_shooting import RedGreenShooting
from patterns.red_green_wipe import RedGreenWipe
from patterns.super_twinkle import SuperTwinkle
from patterns.twinkle import Twinkle


DEFAULT_PROGRAMS = (
  Off,
  Rainbow,
  Demo,
  Basic,
  CandyCane,
  ChristmasChase,
  RedGreenWipe,
  RedGreenShooting,
  Twinkle,
  SuperTwinkle,
)


class LightController:
  """Manages the active LED pattern task on a NeoPixel strip."""

  def __init__(
    self,
    np,
    programs=None,
    brightness=50,
    sleep_modifier=1.0,
    np_factory=None,
    config_path='config.json',
  ):
    self.np = np
    self.string_length = len(np)
    self._np_factory = np_factory
    self.config_path = config_path
    program_list = programs if programs is not None else DEFAULT_PROGRAMS
    if isinstance(program_list, dict):
      self.programs = dict(program_list)
    else:
      self.programs = {p.name: p for p in program_list}
    self.brightness = max(0, min(100, int(brightness)))
    self.sleep_modifier = round(max(0.001, min(10.0, float(sleep_modifier))), 3)
    self.twinkle_mod = TwinkleMod()
    self.wave_mod = WaveMod()
    self.active_program = None
    self._pattern = None
    self._task = None

  def to_config_dict(self):
    return {
      'active_program': self.active_program or 'off',
      'brightness': self.brightness,
      'string_length': self.string_length,
      'sleep_modifier': self.sleep_modifier,
      'twinkle_mod': {
        'enabled': self.twinkle_mod.enabled,
        'count': self.twinkle_mod.count,
      },
      'wave_mod': {
        'direction': self.wave_mod.direction,
        'min_brightness': self.wave_mod.min_brightness,
        'max_brightness': self.wave_mod.max_brightness,
        'width': self.wave_mod.width,
      },
    }

  def save_config(self):
    if not self.config_path:
      return
    try:
      with open(self.config_path, 'w') as fd:
        json.dump(self.to_config_dict(), fd)
    except OSError as exc:
      print('Failed to save config:', exc)

  def load_config(self):
    """Load persisted settings from config_path and return the saved program name."""
    if not self.config_path:
      return 'off'
    try:
      with open(self.config_path) as fd:
        data = json.load(fd)
    except (OSError, ValueError):
      return 'off'

    if 'brightness' in data:
      self.brightness = max(0, min(100, int(data['brightness'])))
    if 'sleep_modifier' in data:
      val = float(data['sleep_modifier'])
      if val > 0:
        self.sleep_modifier = round(max(0.001, min(10.0, val)), 3)

    twinkle_data = data.get('twinkle_mod')
    if isinstance(twinkle_data, dict):
      if 'enabled' in twinkle_data:
        self.twinkle_mod.enabled = bool(twinkle_data['enabled'])
      if 'count' in twinkle_data:
        self.twinkle_mod.count = max(1, int(twinkle_data['count']))

    wave_data = data.get('wave_mod')
    if isinstance(wave_data, dict):
      if 'direction' in wave_data:
        self.wave_mod.direction = int(wave_data['direction'])
      if 'min_brightness' in wave_data:
        self.wave_mod.min_brightness = max(0, min(100, int(wave_data['min_brightness'])))
      if 'max_brightness' in wave_data:
        self.wave_mod.max_brightness = max(0, min(100, int(wave_data['max_brightness'])))
      if self.wave_mod.min_brightness > self.wave_mod.max_brightness:
        self.wave_mod.min_brightness = self.wave_mod.max_brightness
      if 'width' in wave_data:
        self.wave_mod.width = max(2, int(wave_data['width']))

    if 'string_length' in data:
      new_length = max(1, min(1000, int(data['string_length'])))
      if new_length != self.string_length:
        if self._np_factory is not None:
          self.np = self._np_factory(new_length)
        self.string_length = new_length

    saved_program = data.get('active_program', 'off')
    return saved_program if saved_program in self.programs else 'off'

  def list_programs(self):
    return list(self.programs.values())

  def set_brightness(self, value):
    """Set brightness percentage (0-100) and refresh the active pattern."""
    self.brightness = max(0, min(100, int(value)))
    if self._pattern is not None:
      self._pattern.write()
    self.save_config()
    return self.brightness

  def adjust_brightness(self, delta):
    """Adjust brightness percentage by delta, clamped to 0-100."""
    return self.set_brightness(self.brightness + delta)

  def set_sleep_modifier(self, value):
    """Set timing modifier (> 0, up to 3 decimal places, clamped to 0.001-10.0)."""
    val = float(value)
    if val <= 0:
      return self.sleep_modifier
    self.sleep_modifier = round(max(0.001, min(10.0, val)), 3)
    self.save_config()
    return self.sleep_modifier

  def get_base_sleep_ms(self):
    if self._pattern is not None:
      return self._pattern.sleep_ms
    pattern_cls = self.programs.get(self.active_program or 'off')
    return pattern_cls.sleep_ms if pattern_cls is not None else 0

  def get_effective_sleep_ms(self):
    if self._pattern is not None:
      return self._pattern.get_sleep_ms()
    return max(1, int(round(self.get_base_sleep_ms() * self.sleep_modifier)))

  def step_modifications(self):
    self.wave_mod.step(self.string_length)
    self.twinkle_mod.step(self.string_length)

  def apply_modifications(self, index, color):
    color = self.wave_mod.apply(index, color)
    color = self.twinkle_mod.apply(index, color)
    return color

  def set_twinkle_mod(self, enabled=None, count=None):
    if enabled is not None:
      self.twinkle_mod.enabled = bool(enabled)
    if count is not None:
      self.twinkle_mod.count = max(1, min(self.string_length, int(count)))
    if self._pattern is not None:
      self.twinkle_mod.step(self.string_length)
      self._pattern.write()
    self.save_config()

  def set_wave_mod(self, direction=None, min_brightness=None, max_brightness=None, width=None):
    if direction is not None:
      self.wave_mod.direction = int(direction)
    if min_brightness is not None:
      self.wave_mod.min_brightness = max(0, min(100, int(min_brightness)))
    if max_brightness is not None:
      self.wave_mod.max_brightness = max(0, min(100, int(max_brightness)))
    if self.wave_mod.min_brightness > self.wave_mod.max_brightness:
      self.wave_mod.min_brightness = self.wave_mod.max_brightness
    if width is not None:
      self.wave_mod.width = max(2, int(width))
    if self._pattern is not None:
      self._pattern.write()
    self.save_config()

  def set_string_length(self, length):
    """Update the LED string length, rebuild NeoPixel, and restart the active program."""
    new_length = max(1, min(1000, int(length)))
    current_program = self.active_program or 'off'

    if self._task is not None:
      self._task.cancel()
      self._task = None

    for i in range(len(self.np)):
      self.np[i] = (0, 0, 0)
    self.np.write()

    if self._np_factory is not None:
      self.np = self._np_factory(new_length)
    self.string_length = new_length
    self.set_program(current_program, save=False)
    self.save_config()
    return self.string_length

  def set_program(self, name, save=True):
    """Switch to the named program, cancelling any currently running task.

    Returns True if the program exists and was scheduled, False otherwise.
    """
    pattern_cls = self.programs.get(name)
    if pattern_cls is None:
      return False

    if self._task is not None:
      self._task.cancel()
      self._task = None

    self.active_program = name
    self._task = asyncio.create_task(self._run_program(pattern_cls))
    if save:
      self.save_config()
    return True

  async def _run_program(self, pattern_cls):
    try:
      self._pattern = pattern_cls(self.np, controller=self)
      await self._pattern.run()
    except asyncio.CancelledError:
      pass
    except Exception as exc:
      print('Pattern error:', exc)
