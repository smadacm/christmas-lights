from .models import HttpRequest, HttpResponse


pages_dir = './pages'


def render_page(page_name: str, context=None):
  page = f'{pages_dir}/{page_name}'

  resp = HttpResponse()
  with open(page) as fd:
    content = fd.read()

  if context:
    for key, value in context.items():
      val_str = str(value)
      content = content.replace('{{ ' + key + ' }}', val_str)
      content = content.replace('{{' + key + '}}', val_str)
      content = content.replace('{' + key + '}', val_str)

  resp.data = content
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


def register_routes(router, light_controller):
  async def index(request: HttpRequest):
    wave_labels = {0: 'Off', 1: 'Wave', -1: 'Reverse Wave'}
    brightness = light_controller.get_mod('brightness')
    twinkle = light_controller.get_mod('twinkle')
    wave = light_controller.get_mod('wave')
    return render_page('index.html', {
      'active_program': format_program_name(light_controller.active_program),
      'brightness': brightness.level if brightness else 50,
      'string_length': light_controller.string_length,
      'sleep_modifier': light_controller.sleep_modifier,
      'base_sleep_ms': light_controller.get_base_sleep_ms(),
      'effective_sleep_ms': light_controller.get_effective_sleep_ms(),
      'twinkle_status': 'On' if twinkle and twinkle.enabled else 'Off',
      'twinkle_count': twinkle.count if twinkle else 5,
      'twinkle_speed': twinkle.speed if twinkle else 1,
      'wave_status': wave_labels.get(wave.direction if wave else 0, 'Off'),
      'wave_min': wave.min_brightness if wave else 20,
      'wave_max': wave.max_brightness if wave else 100,
      'wave_width': wave.width if wave else 20,
    })

  async def toggle_twinkle(request: HttpRequest):
    twinkle = light_controller.get_mod('twinkle')
    if twinkle is not None:
      light_controller.configure_mod('twinkle', enabled=not twinkle.enabled)
    resp = HttpResponse()
    resp.status = 302
    resp.headers['Location'] = '/'
    return resp

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
  router.add_route(b'/mod/twinkle/toggle', toggle_twinkle)
  router.add_route(b'/mod/twinkle', set_twinkle)
  router.add_route(b'/mod/wave/off', make_wave_direction_handler(light_controller, 0))
  router.add_route(b'/mod/wave/forward', make_wave_direction_handler(light_controller, 1))
  router.add_route(b'/mod/wave/reverse', make_wave_direction_handler(light_controller, -1))
  router.add_route(b'/mod/wave', set_wave)
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