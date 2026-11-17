from .models import HttpRequest, HttpResponse


pages_dir = './pages'


def render_template_str(page_name: str, context=None):
  page = f'{pages_dir}/{page_name}'
  print(f'{page_name} -- {page}')
  with open(page) as fd:
    content = fd.read()

  if context:
    for key, value in context.items():
      val_str = str(value)
      content = content.replace('{{ ' + key + ' }}', val_str)
      content = content.replace('{{' + key + '}}', val_str)
      content = content.replace('{' + key + '}', val_str)

  return content


def render_page(page_name: str, context=None):
  resp = HttpResponse()
  resp.data = render_template_str(page_name, context)
  return resp


def make_program_handler(light_controller, program_name: str):
  async def handler(request: HttpRequest):
    light_controller.set_program(program_name)
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  # handler.__name__ = program_name
  return handler


def make_brightness_adjust_handler(light_controller, delta: int):
  async def handler(request: HttpRequest):
    light_controller.configure_mod('brightness', delta=delta)
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  return handler


def make_brightness_set_handler(light_controller, value: int):
  async def handler(request: HttpRequest):
    light_controller.configure_mod('brightness', level=value)
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  return handler


def format_program_name(name: str):
  words = (name or 'off').replace('_', ' ').split(' ')
  return ' '.join(w[0].upper() + w[1:].lower() if w else '' for w in words)


def make_timing_set_handler(light_controller, value: float):
  async def handler(request: HttpRequest):
    light_controller.set_sleep_modifier(value)
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  return handler


def make_wave_direction_handler(light_controller, direction: int):
  async def handler(request: HttpRequest):
    light_controller.configure_mod('wave', direction=direction)
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  return handler


def make_mod_toggle_handler(light_controller, mod_name: str):
  async def handler(request: HttpRequest):
    mod = light_controller.get_mod(mod_name)
    if mod is not None:
      light_controller.configure_mod(mod_name, enabled=not mod.enabled)
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  return handler


def register_routes(router, light_controller):
  async def index(request: HttpRequest):
    pattern_buttons = '\n'.join(
      '<li><a href="{}">{}</a></li>'.format(
        p.path or '/{}'.format(p.name),
        format_program_name(p.name),
      )
      for p in light_controller.list_programs()
    )

    mod_toggles = '\n'.join(
      '<a href="/mod/{}/toggle">{}: {}</a>'.format(
        mod.name,
        format_program_name(mod.name),
        'On' if mod.enabled else 'Off',
      )
      for mod in light_controller.mods.values()
    )

    mod_blocks = '\n'.join(
      render_template_str(mod.template, mod.get_context())
      for mod in light_controller.mods.values()
      if mod.enabled and mod.template
    )

    return render_page('index.html', {
      'active_program': format_program_name(light_controller.active_program),
      'string_length': light_controller.string_length,
      'sleep_modifier': light_controller.sleep_modifier,
      'base_sleep_ms': light_controller.get_base_sleep_ms(),
      'effective_sleep_ms': light_controller.get_effective_sleep_ms(),
      'pattern_buttons': pattern_buttons,
      'mod_toggles': mod_toggles,
      'mod_blocks': mod_blocks,
    })

  async def set_twinkle(request: HttpRequest):
    try:
      raw_count = request.qs.get(b'count')
      raw_speed = request.qs.get(b'speed')
      light_controller.configure_mod(
        'twinkle',
        count=int(raw_count) if raw_count is not None else None,
        speed=int(raw_speed) if raw_speed is not None else None,
        n=light_controller.string_length,
      )
    except ValueError:
      pass
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  async def set_wave(request: HttpRequest):
    try:
      raw_min = request.qs.get(b'min')
      raw_max = request.qs.get(b'max')
      raw_width = request.qs.get(b'width')
      light_controller.configure_mod(
        'wave',
        min_brightness=int(raw_min) if raw_min is not None else None,
        max_brightness=int(raw_max) if raw_max is not None else None,
        width=int(raw_width) if raw_width is not None else None,
      )
    except ValueError:
      pass
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  async def set_timing(request: HttpRequest):
    raw_mod = request.qs.get(b'modifier')
    if raw_mod is not None:
      try:
        light_controller.set_sleep_modifier(float(raw_mod))
      except ValueError:
        pass
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  async def set_string_length(request: HttpRequest):
    raw_len = request.qs.get(b'length')
    if raw_len is not None:
      try:
        light_controller.set_string_length(int(raw_len))
      except ValueError:
        pass
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

  # router.add_route(path, handler)
  router.add_route(b'/', index)
  router.add_route(b'/string_length', set_string_length)
  router.add_route(b'/timing', set_timing)
  router.add_route(b'/timing/set/0.5', make_timing_set_handler(light_controller, 0.5))
  router.add_route(b'/timing/set/1', make_timing_set_handler(light_controller, 1.0))
  router.add_route(b'/timing/set/2', make_timing_set_handler(light_controller, 2.0))
  router.add_route(b'/mod/twinkle', set_twinkle)
  router.add_route(b'/mod/wave/off', make_wave_direction_handler(light_controller, 0))
  router.add_route(b'/mod/wave/forward', make_wave_direction_handler(light_controller, 1))
  router.add_route(b'/mod/wave/reverse', make_wave_direction_handler(light_controller, -1))
  router.add_route(b'/mod/wave', set_wave)

  for mod_name in light_controller.mods:
    router.add_route('/mod/{}/toggle'.format(mod_name).encode(), make_mod_toggle_handler(light_controller, mod_name))
  router.add_route(b'/brightness/down/5', make_brightness_adjust_handler(light_controller, -5))
  router.add_route(b'/brightness/down/1', make_brightness_adjust_handler(light_controller, -1))
  router.add_route(b'/brightness/up/1', make_brightness_adjust_handler(light_controller, 1))
  router.add_route(b'/brightness/up/5', make_brightness_adjust_handler(light_controller, 5))
  router.add_route(b'/brightness/set/5', make_brightness_set_handler(light_controller, 5))
  router.add_route(b'/brightness/set/50', make_brightness_set_handler(light_controller, 50))
  router.add_route(b'/brightness/set/100', make_brightness_set_handler(light_controller, 100))

  for pattern_cls in light_controller.list_programs():
    raw_path = pattern_cls.path or '/{}'.format(pattern_cls.name)
    path = raw_path.encode() if isinstance(raw_path, str) else raw_path
    router.add_route(path, make_program_handler(light_controller, pattern_cls.name))