#!/usr/bin/env python3

import sys
from argparse import ArgumentParser
from json import loads
from os.path import join
from traceback import print_exc

from PIL import Image
from requests import request
from requests.exceptions import ConnectionError


def print_out(data, level=0, parent=None):  # FIXME
  if isinstance(data, dict):
    for index, (key, value) in enumerate(data.items()):
      if key == "success" and level == 0:
        continue

      if isinstance(value, (dict, list)):
        if len(value):
          print(f"{''.ljust(level)}{key}:")
          print_out(value, level + 2)
        else:
          print(f"{''.ljust(level)}{key}: {value}")
      else:
        if parent == list and index == 0:
          print(f"{''.ljust(level - 2)}- {key}: {value}")
        else:
          print(f"{''.ljust(level)}{key}: {value}")
  elif isinstance(data, list):
    for value in data:
      if isinstance(value, dict):
        print_out(value, level, list)
      else:
        print(f"{''.ljust(level - 2)}- {value}")


def query(args):
  method = None
  url = f"http://localhost:{args.port}"
  data = {}

  if args.action == "info":
    method = "GET"
  elif args.action == "version":
    method = "GET"
    url = join(url, "version")
  elif args.action == "devices":
    method = "GET"
    url = join(url, "device")
    if args.device:
      url = join(url, args.device)
  elif args.action == "announce":
    method = "PUT"
  elif args.action == "commands":
    method = "GET"
    url = join(url, "command")
    if args.device:
      url = join(url, args.device)
  elif args.action == "notifications":
    method = "GET"
    url = join(url, "notification")
    if args.device:
      url = join(url, args.device)
  else:
    if args.action == "device":
      method = "GET"
      url = join(url, "device", args.device)
    elif args.action == "pair":
      method = "POST"
      url = join(url, "pair", args.device)
    elif args.action == "unpair":
      method = "DELETE"
      url = join(url, "unpair", args.device)
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
    elif args.action == "command":
      if args.key:
        method = "DELETE" if args.delete else "PUT"
        url = join(url, "command", args.device, args.key)
      else:
        method = "POST"
        url = join(url, "command", args.device)
      data = {"name": args.name, "command": args.command}
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
    elif args.action == "exec":
      method = "PATCH"
      url = join(url, "command", args.device, args.key)
    else:
      print("Error: action not implemented")
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

  print_out(data)
  sys.exit(int(not data["success"]))


def main():
  parser = ArgumentParser(prog="konnect", add_help=False, allow_abbrev=False)
  parser.add_argument("--port", default=8080, type=int, help="Port running the admin interface")
  parser.add_argument("--debug", action="store_true", help="Show debug messages")

  subparsers = parser.add_subparsers(dest="action", title="actions")
  subparsers.add_parser("announce", help="Announce your identity")

  command = subparsers.add_parser("command", help="Configure local commands...")
  command.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")
  command.add_argument("--delete", action="store_true", help="Delete command")
  is_delete = "--delete" in sys.argv
  delete = command.add_argument_group("delete")
  delete.add_argument("--key", type=str, required=is_delete, help="Command =name or key")
  details = command.add_argument_group("details")
  details.add_argument("--name", type=str, required=not is_delete, help="Name to show")
  details.add_argument("--command", metavar="CMD", type=str, required=not is_delete, help="Command to execute")

  commands = subparsers.add_parser("commands", help="List all commands...")
  commands.add_argument("--device", metavar="DEV", type=str, help="Device @name or id")

  custom = subparsers.add_parser("custom", help="Send custom packet...")
  custom.add_argument("--device", metavar="DEV", type=str, required=True, help="Device @name or id")
  custom.add_argument("--data", type=str, help="JSON string")

  devices = subparsers.add_parser("devices", help="List all devices...")
  devices.add_argument("--device", metavar="DEV", type=str, help="Device @name or id")

  exec_ = subparsers.add_parser("exec", help="Execute remote command...")
  exec_.add_argument("--device", metavar="DEV", type=str, required=True)
  exec_.add_argument("--key", type=str, required=True, help="Command =name or key")

  subparsers.add_parser("info", help="Show server info")

  notifications = subparsers.add_parser("notifications", help="List all notifications...")
  notifications.add_argument("--device", metavar="DEV", type=str, help="Device @name or id")

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
