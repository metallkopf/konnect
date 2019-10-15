#!/usr/bin/env python3

from argparse import ArgumentParser
from os.path import join
from sys import argv

from requests import request


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--port", default=8080, type=int, help="Port running the admin interface")
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("--devices", action="store_true", help="List all devices")
  group.add_argument("--identity", action="store_true", help="Search for devices in the network")
  group.add_argument("--pair", metavar="IDENTIFIER", help="Request pairing to a said device")
  group.add_argument("--unpair", metavar="IDENTIFIER", help="Stop pairing to a said device")
  group.add_argument("--ping", metavar="IDENTIFIER", help="Sends a ping to said device")
  group.add_argument("--device", metavar="IDENTIFIER", help="Display this device")
  group.add_argument("--notification", metavar="IDENTIFIER", help="Sends a notification to said device")
  parser.add_argument("--text", required="--notification" in argv, help="The text of the notification")
  parser.add_argument("--title", required="--notification" in argv, help="The title of the notification")
  parser.add_argument("--application", required="--notification" in argv, help="The app that generated the notification")
  parser.add_argument("--reference", default="", help="A unique notification id")
  args = parser.parse_args()

  method = None
  url = "http://localhost:%d" % args.port
  data = {}

  if args.devices:
    method = "GET"
    url = join(url, "device")
  elif args.device:
    method = "GET"
    url = join(url, "device", args.device)
  elif args.identity:
    method = "POST"
    url = join(url, "identity")
  elif args.pair:
    method = "PUT"
    url = join(url, "device", args.pair)
    data = {"pair": True}
  elif args.unpair:
    method = "PUT"
    url = join(url, "device", args.unpair)
    data = {"pair": False}
  elif args.ping:
    method = "POST"
    url = join(url, "ping", args.ping)
  elif args.notification:
    method = "POST"
    url = join(url, "notification", args.notification)
    data = {"text": args.text, "title": args.title, "application": args.application, "reference": args.reference}

  response = request(method, url, json=data)
  data = response.json()

  if response.status_code != 200:
    print("An error ocurred!")

  if args.devices:
    for identifier, device in data.items():
      print(identifier)
      for key, value in device.items():
        print("  %s: %s" % (key.title(), str(value)))
  elif args.device or args.identity or args.pair or args.unpair or args.ping or args.notification:
    for key, value in data.items():
      print("%s: %s" % (key.title(), str(value)))
