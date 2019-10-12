#!/usr/bin/env python3

from argparse import ArgumentParser
from logging import DEBUG, INFO, basicConfig, root
from platform import node
from uuid import uuid4

from OpenSSL.crypto import Error
from systemd.journal import JournalHandler
from twisted.internet import reactor
from twisted.web.server import Site

from api import API
from certificate import Certificate
from database import Database
from protocols import Discovery, KonnectFactory


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--name", default=node())
  parser.add_argument("--verbose", action="store_true", default=True)
  parser.add_argument("--discovery-port", default=1716, type=int, dest="discovery_port")
  parser.add_argument("--service-port", default=1764, type=int, dest="service_port", choices=range(1716, 1765))
  parser.add_argument("--admin-port", default=8080, type=int, dest="admin_port")
  parser.add_argument("--config-dir", default="", dest="config_dir")
  parser.add_argument("--receiver", action="store_true", default=False)
  args = parser.parse_args()

  level = DEBUG if args.verbose else INFO
  basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)
  root.addHandler(JournalHandler(SYSLOG_IDENTIFIER='konnect'))

  database = Database(args.config_dir)

  try:
    options = Certificate.load_options(args.config_dir)
    identifier = Certificate.extract_identifier(options)
  except (FileNotFoundError, Error):
    identifier = str(uuid4()).replace("-", "")
    Certificate.generate(identifier, args.config_dir)
    options = Certificate.load_options(args.config_dir)

  konnect = KonnectFactory(database, identifier, options)
  discovery = Discovery(identifier, args.name, args.discovery_port, args.service_port)

  reactor.listenTCP(args.service_port, konnect, interface="0.0.0.0")
  reactor.listenUDP(args.discovery_port if args.receiver else 0, discovery, interface="0.0.0.0")
  reactor.listenTCP(args.admin_port, Site(API(konnect, discovery)), interface="127.0.0.1")
  reactor.run()
