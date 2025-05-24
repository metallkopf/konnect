#!/usr/bin/env python3

from argparse import SUPPRESS, ArgumentDefaultsHelpFormatter, ArgumentParser
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
from konnect.factories import KonnectFactory
from konnect.protocols import MAX_TCP_PORT, Discovery


def start(args):
  level = DEBUG if args.debug else INFO

  format_ = "%(levelname)s %(message)s"

  if args.timestamps:
    format_ = "%(asctime)s " + format_

  basicConfig(format=format_, level=level)

  getLogger("PIL").setLevel(WARNING)

  args.config_dir = expanduser(expandvars(args.config_dir))
  makedirs(args.config_dir, exist_ok=True)
  database = Database(join(args.config_dir, "konnect.db"))

  try:
    options = Certificate.load_options(args.config_dir)
    identifier = Certificate.extract_identifier(options)
  except (FileNotFoundError, Error):
    identifier = str(uuid4()).replace("-", "")
    Certificate.generate(identifier, args.config_dir)
    options = Certificate.load_options(args.config_dir)

  def keylog(conn, line):
    with open(expanduser(expandvars(args.sslkeylog)), "a+") as f:
      f.write(line.decode() + "\n")

  if args.sslkeylog and args.debug:
    context = options.getContext()
    context.set_keylog_callback(keylog)

  konnect = KonnectFactory(database, identifier, args.name, options)
  discovery = Discovery(identifier, args.name, args.service_port)

  info(f"Starting Konnectd {__version__} as {args.name}")

  reactor.listenTCP(args.service_port, konnect, interface="0.0.0.0")
  reactor.listenUDP(args.discovery_port, discovery, interface="0.0.0.0")
  site = Site(API(konnect, discovery, database, args.debug))

  if args.admin_port.isdigit():
    reactor.listenTCP(int(args.admin_port), site, interface="127.0.0.1")
  else:
    reactor.listenUNIX(expanduser(expandvars(args.admin_port)), site)

  reactor.run()


def main():
  parser = ArgumentParser(prog="konnectd", add_help=False, allow_abbrev=False, formatter_class=ArgumentDefaultsHelpFormatter)
  parser.add_argument("--name", default=node(), help="Device name")
  parser.add_argument("--debug", action="store_true", default=False, help="Show debug messages")
  parser.add_argument("--discovery-port", metavar="PORT", default=MAX_TCP_PORT, type=int, help="Discovery port")
  parser.add_argument("--service-port", metavar="PORT", default=MAX_TCP_PORT, type=int, help="Service port")
  parser.add_argument("--admin-port", metavar="PORT", default="8080", type=str, help="API (tcp) port or unix socket")
  parser.add_argument("--config-dir", metavar="DIR", default="~/.config/konnect", help="Config directory")
  parser.add_argument("--timestamps", action="store_true", default=False, help="Show timestamps")
  parser.add_argument("--sslkeylog", action="store", default=None, const="~/sslkey.log", nargs="?", help=SUPPRESS)
  parser.add_argument("--version", action="store_true", help="Version information")
  parser.add_argument("--help", action="store_true", help=SUPPRESS)

  args = parser.parse_args()

  if args.help:
    parser.print_help()
  elif args.version:
    print(f"Konnectd {__version__}")
  else:
    start(args)


if __name__ == "__main__":
  main()
