#!/usr/bin/env python3


from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from logging import DEBUG, INFO, basicConfig, info
from os import makedirs
from os.path import expanduser
from platform import node
from sys import exit
from uuid import uuid4

from OpenSSL.crypto import Error
from twisted.internet import reactor
from twisted.web.server import Site

from konnect import __version__
from konnect.api import API
from konnect.certificate import Certificate
from konnect.database import Database
from konnect.protocols import Discovery, KonnectFactory


def main():
  parser = ArgumentParser(prog="konnectd", add_help=False, allow_abbrev=False, formatter_class=ArgumentDefaultsHelpFormatter)
  parser.add_argument("--name", default=node(), help="Device name")
  parser.add_argument("--verbose", action="store_true", default=False, help="Show debug messages")
  parser.add_argument("--discovery-port", default=1716, type=int, dest="discovery_port", help="Protocol discovery port")
  parser.add_argument("--service-port", default=1764, type=int, dest="service_port", help="Protocol service port")
  parser.add_argument("--admin-port", default=8080, type=int, dest="admin_port", help="Admin Rest API port")
  parser.add_argument("--config-dir", default="~/.config/konnect", dest="config_dir", help="Config directory")
  parser.add_argument("--receiver", action="store_true", default=False, help="Listen for new devices")
  parser.add_argument("--service", action="store_true", default=False, help="Send logs to journald")
  parser.add_argument("--help", action="store_true", help="This help")
  parser.add_argument("--version", action="store_true", help="Version information")

  args = parser.parse_args()

  if args.help:
    parser.print_help()
    exit()
  elif args.version:
    print(f"Konnectd {__version__}")
    exit()

  level = DEBUG if args.verbose else INFO

  if args.service is True:
    try:
      from systemd.journal import JournalHandler

      handler = JournalHandler(SYSLOG_IDENTIFIER="konnectd")
      basicConfig(format="%(levelname)s %(message)s", level=level, handlers=[handler])
    except ImportError:
      print("systemd-python is not installed")
      exit(1)
  else:
    basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

  args.config_dir = expanduser(args.config_dir)
  makedirs(args.config_dir, exist_ok=True)
  database = Database(args.config_dir)

  try:
    options = Certificate.load_options(args.config_dir)
    identifier = Certificate.extract_identifier(options)
  except (FileNotFoundError, Error):
    identifier = str(uuid4()).replace("-", "")
    Certificate.generate(identifier, args.config_dir)
    options = Certificate.load_options(args.config_dir)

  konnect = KonnectFactory(database, identifier, args.name, options)
  discovery = Discovery(identifier, args.name, args.discovery_port, args.service_port)
  info(f"Starting Konnectd {__version__} as {args.name}")
  reactor.listenTCP(args.service_port, konnect, interface="0.0.0.0")
  reactor.listenUDP(args.discovery_port if args.receiver else 0, discovery, interface="0.0.0.0")
  reactor.listenTCP(args.admin_port, Site(API(konnect, discovery)), interface="127.0.0.1")
  reactor.run()


if __name__ == "__main__":
  main()
