#!/usr/bin/env python3

import sys
from argparse import ArgumentParser
from json import dumps, loads
from os.path import join
from traceback import print_exc

from PIL import Image
from requests import request
from requests.exceptions import ConnectionError


def query(args):
  method = None
  url = f"http://localhost:{args.port}"
  data = {}

  if args.action == "version":
    method = "GET"
  elif args.action == "devices":
    method = "GET"
    url = join(url, "device")
  elif args.action == "announce":
    method = "PUT"
  else:
    if args.action == "device":
      method = "GET"
      url = join(url, "device", args.device)
    elif args.action == "pair":
      method = "POST"
      url = join(url, "device", args.device)
    elif args.action == "unpair":
      method = "DELETE"
      url = join(url, "device", args.device)
    elif args.action == "ring":
      method = "POST"
      url = join(url, "ring", args.device)
    elif args.action == "ping":
      method = "POST"
      url = join(url, "ping", args.device)
    elif args.action == "custom":
      method = "POST"
      url = join(url, "custom", args.device)
      try:
        data = loads(args.data)
      except Exception:
        print("Error: invalid json")
        sys.exit(1)
    elif args.action == "notification":
      if args.cancel:
        method = "DELETE"
        url = join(url, "notification", args.device, args.reference)
      else:
        method = "POST"
        url = join(url, "notification", args.device)
        data = {"text": args.text, "title": args.title, "application": args.application, "reference": args.reference}

        if args.icon:
          try:
            with Image.open(args.icon):
              data["icon"] = args.icon
          except ValueError:
            print("Error: unsupported icon format")
            sys.exit(1)
          except FileNotFoundError:
            print("Error: icon not found")
            sys.exit(1)

  if args.debug:
    print("REQUEST:", method, url)
    print("", data)

  try:
    response = request(method, url, json=data, timeout=60)
  except ConnectionError:
    print("ERROR: cannot connect to server")
    sys.exit(1)

  if args.debug:
    print("RESPONSE:", response.status_code, response.headers.get("content-type"))
    print("", response.text)

  try:
    if len(response.text):
      data = response.json()
  except Exception as e:
    print("EXCEPTION:")
    print_exc(e)
    data = {}
    print()

  print(dumps(data, indent=2))
  sys.exit(int(data["success"]))


def main():
  parser = ArgumentParser(prog="konnect", add_help=False, allow_abbrev=False)
  parser.add_argument("--port", default=8080, type=int, help="Port running the admin interface")
  parser.add_argument("--debug", action="store_true", help="Show debug messages")

  subparsers = parser.add_subparsers(dest="action", title="actions")
  subparsers.add_parser("announce", help="Announce your identity")

  custom = subparsers.add_parser("custom", help="Send custom packet...")
  custom.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")
  custom.add_argument("--data", type=str, help="JSON string")

  device = subparsers.add_parser("device", help="Show device info")  # FIXME
  device.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")

  subparsers.add_parser("devices", help="List devices")


  notification = subparsers.add_parser("notification", help="Send or cancel notification...")
  notification.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")
  notification.add_argument("--cancel", action="store_true", help="Cancel notification")
  is_cancel = "--cancel" in sys.argv
  cancel = notification.add_argument_group("cancel")
  cancel.add_argument("--reference", type=str, required=is_cancel, help="Reference")
  message = notification.add_argument_group("message")
  message.add_argument("--title", type=str, required=not is_cancel, help="Title")
  message.add_argument("--text", type=str, required=not is_cancel, help="Text")
  message.add_argument("--application", type=str, required=not is_cancel, help="Application")
  message.add_argument("--icon", type=str, help="Icon (filename)")

  pair = subparsers.add_parser("pair", help="Pair with device...")
  pair.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")

  ping = subparsers.add_parser("ping", help="Send ping...")
  ping.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")

  ring = subparsers.add_parser("ring", help="Ring my device...")
  ring.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")

  unpair = subparsers.add_parser("unpair", help="Unpair trusted device...")
  unpair.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")

  subparsers.add_parser("version", help="Show server version")
  subparsers.add_parser("help", help="This")

  args = parser.parse_args()

  if args.action in [None, "help"]:
    parser.print_help()
    sys.exit(0)

  query(args)


if __name__ == "__main__":
  main()
