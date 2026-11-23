import asyncio
import gc
import json

from patterns.basic import Basic
from patterns.chase import Chase
from patterns.demo import Demo
from patterns.modifications import BrightnessMod, TwinkleMod, WaveMod
from patterns.off import Off
from patterns.rainbow import Rainbow
from patterns.shooting import Shooting
from patterns.twinkle import Twinkle
from patterns.wipe import Wipe
from patterns.wipe_shoot import WipeShoot

DEFAULT_ACTIONS = (
  Off,
  Rainbow,
  Demo,
  Basic,
  Chase,
  Wipe,
  WipeShoot,
  Shooting,
  Twinkle,
  BrightnessMod,
  WaveMod,
  TwinkleMod,
)


class LightController:
  """Executes a pipeline of Action objects and writes the final frame to NeoPixels."""

  def __init__(
    self,
    np,
    actions_registry=None,
    sleep_modifier=1.0,
    np_factory=None,
    config_path='config.json',
  ):
    self.np = np
    self.string_length = len(np)
    self._np_factory = np_factory
    self.config_path = config_path

    reg = actions_registry if actions_registry is not None else DEFAULT_ACTIONS
    if isinstance(reg, dict):
      self.registry = dict(reg)
    else:
      self.registry = {a.name: a for a in reg}

    self.sleep_modifier = round(max(0.001, min(10.0, float(sleep_modifier))), 3)
    self.actions = []
    self._task = None
    self._running = False
    self._refresh_np_meta()

  def _refresh_np_meta(self):
    self._buf = getattr(self.np, 'buf', None)
    self._bpp = getattr(self.np, 'bpp', 3)
    order = getattr(self.np, 'ORDER', (1, 0, 2, 3))
    self._o0 = order[0]
    self._o1 = order[1]
    self._o2 = order[2]

  def list_action_names(self):
    return list(self.registry.keys())

  def get_config(self):
    return {
      'string_length': self.string_length,
      'sleep_modifier': self.sleep_modifier,
      'actions': [action.to_dict() for action in self.actions],
    }

  def save_config(self):
    if not self.config_path:
      return
    try:
      with open(self.config_path, 'w') as fd:
        json.dump(self.get_config(), fd)
    except OSError as exc:
      print('Failed to save config:', exc)

  def load_config(self):
    """Load persisted configuration from config_path, or default to [{'name': 'off'}]."""
    default_cfg = {
      'string_length': self.string_length,
      'sleep_modifier': self.sleep_modifier,
      'actions': [{'name': 'off', 'params': {}}],
    }
    if not self.config_path:
      return default_cfg
    try:
      with open(self.config_path) as fd:
        data = json.load(fd)
      if isinstance(data, dict) and 'actions' in data:
        return data
    except (OSError, ValueError):
      pass
    return default_cfg

  def apply_config(self, config, save=True, force=False):
    """Update string_length, sleep_modifier, and active action pipeline.

    Preserves matching prefix actions so changing a trailing modifier does not
    reset an active pattern unless force=True or string_length changed.
    """
    if not isinstance(config, dict):
      raise ValueError('config must be a JSON object')

    if 'sleep_modifier' in config:
      val = float(config['sleep_modifier'])
      if val > 0:
        self.sleep_modifier = round(max(0.001, min(10.0, val)), 3)

    length_changed = False
    if 'string_length' in config:
      new_length = max(1, min(1000, int(config['string_length'])))
      if new_length != self.string_length:
        length_changed = True
        self._stop_task()
        for i in range(len(self.np)):
          self.np[i] = (0, 0, 0)
        self.np.write()
        if self._np_factory is not None:
          self.np = self._np_factory(new_length)
          self._refresh_np_meta()
        self.string_length = new_length

    raw_actions = config.get('actions', [{'name': 'off', 'params': {}}])
    if not isinstance(raw_actions, list) or len(raw_actions) == 0:
      raw_actions = [{'name': 'off', 'params': {}}]

    parsed_specs = []
    for entry in raw_actions:
      if not isinstance(entry, dict):
        continue
      name = entry.get('name')
      action_cls = self.registry.get(name)
      if action_cls is None:
        raise ValueError('Unknown action: {}'.format(name))
      params = entry.get('params') or {}
      parsed_specs.append((action_cls, params))

    if not parsed_specs:
      parsed_specs.append((Off, {}))

    if force or length_changed:
      mismatch_idx = 0
    else:
      mismatch_idx = 0
      limit = min(len(self.actions), len(parsed_specs))
      while mismatch_idx < limit:
        existing = self.actions[mismatch_idx]
        action_cls, params = parsed_specs[mismatch_idx]
        if existing.name != action_cls.name:
          break
        candidate = action_cls(self.string_length, **params)
        if existing.get_params() != candidate.get_params():
          break
        mismatch_idx += 1

    self.actions = self.actions[:mismatch_idx]
    for action_cls, params in parsed_specs[mismatch_idx:]:
      self.actions.append(action_cls(self.string_length, **params))
    gc.collect()

    if save:
      self.save_config()

    if not self._running or self._task is None:
      self._task = asyncio.create_task(self._run_loop())

    return self.get_config()

  def reload(self):
    """Stop the current task, reload config.json, and restart all actions."""
    self._stop_task()
    self.actions = []
    gc.collect()
    cfg = self.load_config()
    return self.apply_config(cfg, save=False, force=True)

  def _stop_task(self):
    if self._task is not None:
      self._task.cancel()
      self._task = None
    self._running = False

  def _write_pixels(self, pixels):
    n = self.string_length
    buf = self._buf
    if buf is not None and self._bpp == 3:
      o0, o1, o2 = self._o0, self._o1, self._o2
      for i in range(n):
        c = pixels[i]
        j = i * 3
        buf[j + o0] = c[0]
        buf[j + o1] = c[1]
        buf[j + o2] = c[2]
    else:
      np = self.np
      for i in range(n):
        np[i] = pixels[i]

    gc.disable()
    self.np.write()
    gc.enable()

  async def _run_loop(self):
    self._running = True
    try:
      await asyncio.sleep_ms(0)
      n = self.string_length
      pixels = [(0, 0, 0)] * n

      while True:
        actions = self.actions
        for i in range(n):
          pixels[i] = (0, 0, 0)

        base_sleep = 0
        should_loop = False
        for action in actions:
          pixels = action.apply(pixels)
          if action.loop:
            should_loop = True
          if action.sleep_ms > base_sleep:
            base_sleep = action.sleep_ms

        self._write_pixels(pixels)
        await asyncio.sleep_ms(0)

        if not should_loop:
          break

        sleep_ms = max(10, int(round((base_sleep or 50) * self.sleep_modifier)))
        await asyncio.sleep_ms(sleep_ms)
    except asyncio.CancelledError:
      pass
    except Exception as exc:
      print('Action loop error:', exc)
    finally:
      self._running = False
