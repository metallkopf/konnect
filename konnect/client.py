#!/usr/bin/env python3

from argparse import ArgumentParser
from base64 import b64encode
from os import unlink
from os.path import join
from sys import argv, exit
from tempfile import mkstemp

from PIL import Image
from PIL.Image import Resampling
from requests import request

from konnect import __version__


MAX_ICON_SIZE = 128


def main():
  parser = ArgumentParser(prog="konnect", add_help=False, allow_abbrev=False)
  parser.add_argument("--port", default=8080, type=int, help="Port running the admin interface")
  parser.add_argument("--debug", action="store_true", default=False, help="Show debug messages")

  root = parser.add_argument_group("arguments")
  main = root.add_mutually_exclusive_group(required=True)
  main.add_argument("--devices", action="store_true", help="List all devices")
  main.add_argument("--announce", action="store_true", help="Search for devices in the network")
  main.add_argument("--command", choices=["info", "pair", "unpair", "ring", "ping", "notification", "cancel"])
  main.add_argument("--help", action="store_true", help="This help")
  main.add_argument("--version", action="store_true", help="Version information")

  is_command = "--command" in argv
  command = parser.add_argument_group("command arguments")
  selector = command.add_mutually_exclusive_group(required=is_command)
  selector.add_argument("--identifier", metavar="ID", help="Device Identifier")
  selector.add_argument("--name", help="Device Name")

  is_notification = is_command and "notification" in argv
  message = parser.add_argument_group("notification arguments")
  message.add_argument("--text", help="The text of the notification", required=is_notification)
  message.add_argument("--title", help="The title of the notification", required=is_notification)
  message.add_argument("--application", metavar="APP", help="The app that generated the notification", required=is_notification)
  message.add_argument("--reference", metavar="REF", default="", help="An (optional) unique notification id")
  message.add_argument("--icon", default=None, help="The icon of the notification (optional)")

  is_cancel = is_command and "cancel" in argv
  dismiss = parser.add_argument_group("cancel arguments")
  dismiss.add_argument("--reference2", metavar="REF2", help="Notification id", required=is_cancel)

  args = parser.parse_args()

  if args.help:
    parser.print_help()
    exit()
  elif args.version:
    print(f"Konnect {__version__}")
    exit()

  method = None
  url = f"http://localhost:{args.port}"
  data = {}

  if args.devices:
    method = "GET"
    url = join(url, "device")
  elif args.announce:
    method = "POST"
    url = join(url, "announce")
  else:
    key = "identifier" if args.identifier else "name"
    value = args.identifier or args.name

    if args.command == "info":
      method = "GET"
      url = join(url, "device", key, value)
    elif args.command == "pair":
      method = "POST"
      url = join(url, "device", key, value)
    elif args.command == "unpair":
      method = "DELETE"
      url = join(url, "device", key, value)
    elif args.command == "ring":
      method = "POST"
      url = join(url, "ring", key, value)
    elif args.command == "ping":
      method = "POST"
      url = join(url, "ping", key, value)
    elif args.command == "notification":
      method = "POST"
      url = join(url, "notification", key, value)
      data = {"text": args.text, "title": args.title, "application": args.application, "reference": args.reference}

      if args.icon:
        try:
          path = args.icon

          with Image.open(args.icon) as image:
            if image.format != "PNG" or max(image.size) > MAX_ICON_SIZE:
              _, path = mkstemp()
              image.thumbnail([MAX_ICON_SIZE] * 2, Resampling.LANCZOS)
              image.save(path, "PNG")

          with open(path, "rb") as handle:
            icon = b64encode(handle.read())
            data["icon"] = icon.decode()

          if args.icon != path:
            unlink(path)
        except ValueError:
          print("Error: unsupported icon format")
          exit(1)
        except FileNotFoundError:
          print("Error: icon not found")
          exit(1)
    elif args.command == "cancel":
      method = "DELETE"
      url = join(url, "notification", key, value, args.reference2)

  if args.debug:
    print("REQUEST:", method, url)
    print("", data)

  response = request(method, url, json=data)

  if args.debug:
    print("RESPONSE:", response.status_code, response.headers.get("content-type"))
    print("", response.text)

  data = response.json()

  if response.status_code != 200:
    print("An error ocurred!")

  if args.devices:
    for device in data["devices"]:
      print("- {name}: {identifier} (Trusted: {trusted}, Reachable: {reachable})".format(**device))
  elif args.command is not None:
    for key, value in data.items():
      print(f"{key.title()}: {value}")


if __name__ == "__main__":
  main()
