import asyncio
import gc
import json

from patterns.basic import Basic
from patterns.candy_cane import CandyCane
from patterns.christmas_chase import ChristmasChase
from patterns.demo import Demo
from patterns.modifications import BrightnessMod, TwinkleMod, WaveMod
from patterns.off import Off
from patterns.rainbow import Rainbow
from patterns.red_green_shooting import RedGreenShooting
from patterns.red_green_wipe import RedGreenWipe
from patterns.red_green_wipe_shoot import RedGreenWipeShoot
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
  RedGreenWipeShoot,
  RedGreenShooting,
  Twinkle,
  SuperTwinkle,
)


DEFAULT_MODS = (
  BrightnessMod,
  WaveMod,
  TwinkleMod,
)


class LightController:
  """Manages the active LED pattern task on a NeoPixel strip."""

  def __init__(
    self,
    np,
    programs=None,
    mods=None,
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

    mod_list = mods if mods is not None else DEFAULT_MODS
    if isinstance(mod_list, dict):
      self.mods = dict(mod_list)
    else:
      self.mods = {m.name: m() for m in mod_list}

    self.sleep_modifier = round(max(0.001, min(10.0, float(sleep_modifier))), 3)
    self.active_program = None
    self._pattern = None
    self._task = None

  def to_config_dict(self):
    return {
      'active_program': self.active_program or 'off',
      'string_length': self.string_length,
      'sleep_modifier': self.sleep_modifier,
      'mods': {name: mod.to_dict() for name, mod in self.mods.items()},
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

    if 'sleep_modifier' in data:
      val = float(data['sleep_modifier'])
      if val > 0:
        self.sleep_modifier = round(max(0.001, min(10.0, val)), 3)

    mods_data = data.get('mods')
    if isinstance(mods_data, dict):
      for name, mod_data in mods_data.items():
        mod = self.mods.get(name)
        if mod is not None:
          mod.load_dict(mod_data)

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
    for mod in self.mods.values():
      mod.step(self.string_length)

  def get_mod(self, name):
    return self.mods.get(name)

  def configure_mod(self, name, **kwargs):
    mod = self.mods.get(name)
    if mod is None:
      return None
    mod.configure(**kwargs)
    mod.step(self.string_length)
    if self._pattern is not None:
      self._pattern.write()
    self.save_config()
    return mod

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

    if self._pattern is not None:
      self._pattern = None
      gc.collect()

    self.active_program = name
    self._task = asyncio.create_task(self._run_program(pattern_cls))
    if save:
      self.save_config()
    return True

  async def _run_program(self, pattern_cls):
    pattern = None
    try:
      await asyncio.sleep_ms(0)
      gc.collect()
      pattern = pattern_cls(self.np, controller=self)
      self._pattern = pattern
      await pattern.run()
    except asyncio.CancelledError:
      if self._pattern is pattern:
        self._pattern = None
      pattern = None
      gc.collect()
    except Exception as exc:
      print('Pattern error:', exc)
      if self._pattern is pattern:
        self._pattern = None
      pattern = None
      gc.collect()
