import asyncio
import network

from .models import HttpRequest, HttpResponse
from .routes import register_routes

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 80


response_404 = '\r\n'.join([
  'HTTP/1.1 404 Not Found',
  'Content-Type: text/html',
  'Content-Length: 0',
  'Connection: close',
])


class Router:
  def __init__(self):
    print('init router')
    self.routes = {}
    self._lock = asyncio.Lock()

  async def __aenter__(self):
      return srv
  
  def add_route(self, path, handler):
    self.routes[path] = handler

  async def handle_404(self, request: HttpRequest):
    print('handle 404')
    response = HttpResponse()
    response.status = 404
    response.data = 'Not Found'
    return response

  def handle_500(self, request: HttpRequest, error='Internal Server Error'):
    print('handle 500')
    response = HttpResponse()
    response.status = 500
    response.data = error
    return response
  
  async def handle_request(self, reader, writer):
    async with self._lock:
      print('handle request')
      try:
        request = await HttpRequest.from_reader(reader)
        if request is None:
          print('Empty request / Client Disconnected')
          return

        print('Request:', request)

        handler = self.routes.get(request.path, self.handle_404)
        # print('Handler:', handler.__name__)
        response = await handler(request)

        if type(response) != HttpResponse:
          response = self.handle_500(request, 'Handler did not return a response object')

        writer.write(response.render())
        await writer.drain()
      except OSError as exc:
        print('Client connection error:', exc)
      finally:
        try:
          writer.close()
          await writer.wait_closed()
        except OSError:
          pass
        print('Client Disconnected')

async def start_web_server(light_controller, scheduler=None):
  print('start_web_server')

  wlan = network.WLAN(network.STA_IF)

  # setup router
  router = Router()
  register_routes(router, light_controller, scheduler=scheduler)

  # run server
  await asyncio.start_server(router.handle_request, LISTEN_HOST, LISTEN_PORT)

  # print details to console
  print(f'Server running on port {LISTEN_PORT}...')
  print('IP Address:', wlan.ifconfig()[0])

  # Keep the event loop running
  while True:
    await asyncio.sleep(3600)