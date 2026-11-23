import json

from .models import HttpRequest, HttpResponse

WORKER_NAME = 'lights_worker'
WORKER_VERSION = 'v0.0.1'


def register_routes(router, light_controller):
  async def info(request: HttpRequest):
    resp = HttpResponse()
    resp.data = {
      'name': WORKER_NAME,
      'version': WORKER_VERSION,
    }
    return resp

  async def lights(request: HttpRequest):
    resp = HttpResponse()
    if request.method == b'POST':
      try:
        payload = json.loads(request.body or '{}')
        resp.data = light_controller.apply_config(payload)
      except (ValueError, TypeError, OSError) as exc:
        resp.status = 400
        resp.data = {'error': str(exc)}
      return resp

    if request.method == b'GET':
      resp.data = light_controller.get_config()
      return resp

    resp.status = 405
    resp.data = {'error': 'Method Not Allowed'}
    return resp

  async def reload_lights(request: HttpRequest):
    resp = HttpResponse()
    if request.method != b'POST':
      resp.status = 405
      resp.data = {'error': 'Method Not Allowed'}
      return resp
    try:
      resp.data = light_controller.reload()
    except (ValueError, TypeError, OSError) as exc:
      resp.status = 500
      resp.data = {'error': str(exc)}
    return resp

  router.add_route(b'/', info)
  router.add_route(b'/lights', lights)
  router.add_route(b'/lights/reload', reload_lights)
