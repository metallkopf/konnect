#!/usr/bin/env python3

from argparse import ArgumentParser
from os.path import join
from sys import argv

from requests import request


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--port", default=8080, type=int)
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("--devices", action="store_true")
  group.add_argument("--identity", action="store_true")
  group.add_argument("--pair", metavar="IDENTIFIER")
  group.add_argument("--unpair", metavar="IDENTIFIER")
  group.add_argument("--ping", metavar="IDENTIFIER")
  group.add_argument("--device", metavar="IDENTIFIER")
  group.add_argument("--notification", metavar="IDENTIFIER")
  parser.add_argument("--text", required="--notification" in argv)
  parser.add_argument("--title", required="--notification" in argv)
  parser.add_argument("--application", required="--notification" in argv)
  parser.add_argument("--reference", default="")
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
