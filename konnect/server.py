#!/usr/bin/env python3

import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from logging import DEBUG, INFO, WARNING, basicConfig, getLogger, info
from os import makedirs
from os.path import expanduser, expandvars, join
from platform import node
from uuid import uuid4

from OpenSSL.crypto import Error
from twisted.internet import reactor
from twisted.web.server import Site

from konnect import __version__
from konnect.api import API
from konnect.certificate import Certificate
from konnect.database import Database
from konnect.factories import KonnectFactory, TransferFactory
from konnect.protocols import MAX_PORT, MIN_PORT, Discovery


def start(args):
  level = DEBUG if args.debug else INFO

  if args.service is True:
    try:
      from systemd.journal import JournalHandler

      handler = JournalHandler(SYSLOG_IDENTIFIER="konnectd")
      basicConfig(format="%(levelname)s %(message)s", level=level, handlers=[handler])
    except ImportError:
      print("systemd-python is not installed")
      sys.exit(1)
  else:
    basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

  getLogger("PIL").setLevel(WARNING)

  args.config_dir = expanduser(args.config_dir)
  makedirs(args.config_dir, exist_ok=True)
  database = Database(join(args.config_dir, "konnect.db"))

  try:
    options = Certificate.load_options(args.config_dir)
    identifier = Certificate.extract_identifier(options)
  except (FileNotFoundError, Error):
    identifier = str(uuid4()).replace("-", "")
    Certificate.generate(identifier, args.config_dir)
    options = Certificate.load_options(args.config_dir)

  transfer = TransferFactory(args.transfer_port, args.max_transfer_ports)
  konnect = KonnectFactory(database, identifier, args.name, options, transfer)
  discovery = Discovery(identifier, args.name, args.discovery_port, args.service_port)

  info(f"Starting Konnectd {__version__} as {args.name}")

  reactor.listenTCP(args.service_port, konnect, interface="0.0.0.0")

  for x in range(args.max_transfer_ports):
    reactor.listenSSL(args.transfer_port - x, transfer, options, backlog=0, interface="0.0.0.0")

  reactor.listenUDP(args.discovery_port if args.receiver else 0, discovery, interface="0.0.0.0")
  site = Site(API(konnect, discovery, database, args.debug))

  if args.admin_bind == "tcp":
    reactor.listenTCP(args.admin_port, site, interface="127.0.0.1")
  elif args.admin_bind == "socket":
    reactor.listenUNIX(expandvars(args.admin_socket), site)

  reactor.run()


def main():
  parser = ArgumentParser(prog="konnectd", add_help=False, allow_abbrev=False, formatter_class=ArgumentDefaultsHelpFormatter)
  parser.add_argument("--name", default=node(), help="Device name")
  parser.add_argument("--debug", action="store_true", default=False, help="Show debug messages")
  parser.add_argument("--discovery-port", metavar="PORT", default=MIN_PORT, type=int, help="Discovery port")
  parser.add_argument("--service-port", metavar="PORT", default=MAX_PORT, type=int, help="Service port")
  parser.add_argument("--transfer-port", metavar="PORT", default=MAX_PORT - 1, type=int, help="Transfer port (top)")
  parser.add_argument("--max-transfer-ports", metavar="NUM", default=3, type=int, help="Total open ports for transfer")
  parser.add_argument("--admin-port", metavar="PORT", default=8080, type=int, help="API port")
  parser.add_argument("--admin-socket", metavar="SOCK", default="${XDG_RUNTIME_DIR}/konnectd.sock", type=str, help="API unix socket")
  parser.add_argument("--admin-bind", metavar="BIND", default="tcp", choices=["tcp", "socket"], type=str, help="API bind type (tcp or socket)")
  parser.add_argument("--config-dir", metavar="DIR", default="~/.config/konnect", help="Config directory")
  parser.add_argument("--receiver", action="store_true", default=False, help="Listen for new devices")
  parser.add_argument("--service", action="store_true", default=False, help="Send logs to journald")
  parser.add_argument("--help", action="store_true", help="This")
  parser.add_argument("--version", action="store_true", help="Version information")

  args = parser.parse_args()

  if args.help:
    parser.print_help()
  elif args.version:
    print(f"Konnectd {__version__}")
  else:
    start(args)


if __name__ == "__main__":
  main()
