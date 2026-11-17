import asyncio
import json

class HttpRequest:
  @classmethod
  async def from_reader(cls, reader: asyncio.StreamReader):
    request = cls(reader=reader)
    await request.load_headers()
    if not request.header_lines:
      return None
    await request.load_body()
    return request

  def __init__(self, reader=None):
    self.reader = reader # save this to implement reading post body later
    self.header_lines = []
    self.headers = {}
    self.body = ''

    self.method = ''
    self.path = ''
    self.qs = {}
    self.qs_raw = ''
    self.version = ''

  async def load_headers(self):
    lines = []
    while True:
      line = await self.reader.readline()
      if not line:
        break
      if line == b'\r\n':
        break
      lines.append(line)

    self.header_lines = lines
    self.parse_headers()

  def parse_headers(self):
    header_lines = self.header_lines
    if not header_lines:
      return

    parts = header_lines[0].rstrip(b'\r\n').split(b' ')
    if len(parts) < 3:
      return
    self.method, path, self.version = parts[0], parts[1], parts[2]

    path_parts = path.split(b'?', 1)
    self.path = path_parts[0]
    if len(path_parts) > 1:
      self.qs_raw = path_parts[1]
      self.qs = dict([
        param.split(b'=', 1)
        for param in self.qs_raw.split(b'&')
        if b'=' in param
      ])

    self.headers = dict([
      line.rstrip(b'\r\n').split(b': ', 1)
      for line in header_lines[1:]
      if b': ' in line
    ])

  async def load_body(self):
    content_length = 0
    for k, v in self.headers.items():
      if k.lower() == b'content-length':
        try:
          content_length = int(v)
        except ValueError:
          content_length = 0
        break
    if content_length > 0:
      raw = await self.reader.readexactly(content_length)
      self.body = raw.decode()


response_404 = '\r\n'.join([
  'HTTP/1.1 404 Not Found',
  'Content-Type: text/html',
  'Content-Length: 0',
  'Connection: close',
])

response_status_codes = {
    '200': 'OK',
    '204': 'No Content',
    '301': 'Moved Permanently',
    '302': 'Found',
    '400': 'Bad Request',
    '401': 'Unauthorized',
    '403': 'Forbidden',
    '404': 'Not Found',
    '405': 'Method Not Allowed',
    '406': 'Not Acceptable',
    '415': 'Unsupported Media Type',
    '500': 'Internal Server Error',
}

class HttpResponse:
  def __init__(self):
    self.data = None
    self.content_type = None #'text/html'
    self.status = 200
    self.headers = {}

  def _status_line(self):
    return 'HTTP/1.1 {} {}'.format(self.status, response_status_codes[str(self.status)])

  def render_headers(self, body=None):
    if body is None:
      body = self.render_data()

    headers = [
      self._status_line(),
      f'Content-Length: {len(body)}',
    ]

    if not self.content_type:
      if type(self.data) == dict:
        self.content_type = 'application/json'
      else:
        self.content_type = 'text/html'

    if self.content_type:
      headers.append(f'Content-Type: {self.content_type}')

    for key, value in self.headers.items():
      headers.append(f'{key}: {value}')

    return '\r\n'.join(headers)

  def render_data(self):
    if type(self.data) == dict:
      return json.dumps(self.data)
    return self.data or ''

  def render(self):
    body = self.render_data()
    return '{}\r\n\r\n{}'.format(self.render_headers(body), body)