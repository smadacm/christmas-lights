import json
import time

import network


def connect_wifi(secrets_path='secrets.json', timeout_s=20):
  with open(secrets_path) as fd:
    secrets = json.load(fd)

  net_cfg = secrets['network']
  wlan = network.WLAN(network.STA_IF)
  wlan.active(True)

  if not wlan.isconnected():
    print('Connecting to Wi-Fi:', net_cfg['ssid'])
    wlan.connect(net_cfg['ssid'], net_cfg['key'])
    deadline = time.time() + timeout_s
    while not wlan.isconnected():
      if time.time() > deadline:
        raise RuntimeError('Wi-Fi connection timed out')
      time.sleep_ms(250)

  print('Wi-Fi connected:', wlan.ifconfig()[0])
  return wlan


connect_wifi()
