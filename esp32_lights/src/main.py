import asyncio

import machine
import neopixel

from controller import LightController
from server.web import start_web_server

PIN = 5  # D1 (ESP8266), D5 (ESP32)
STRING_LENGTH = 220


def create_np(length):
  return neopixel.NeoPixel(
    machine.Pin(PIN, machine.Pin.OUT),
    length,
    timing=1,
  )


async def main():
  np = create_np(STRING_LENGTH)
  controller = LightController(np, np_factory=create_np)
  initial_program = controller.load_config()
  controller.set_program(initial_program, save=False)
  await start_web_server(controller)


asyncio.run(main())
