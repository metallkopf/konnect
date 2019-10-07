#!/usr/bin/env python3

from twisted.internet import reactor
from twisted.web.server import Site
from os.path import exists
from logging import basicConfig, DEBUG, INFO
from argparse import ArgumentParser
from uuid import uuid4
from platform import node
from protocols import KonnectFactory, Discovery
from api import API
from database import Database
from certificate import Certificate


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--name", default=node())
  parser.add_argument("--debug", action="store_true", default=True)
  args = parser.parse_args()

  level = DEBUG if args.debug else INFO
  basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

  database = Database()

  identifier = Certificate.load_identifier()
  if identifier is None:
    identifier = str(uuid4()).replace("-", "")

  Certificate.generate(identifier)
  options = Certificate.load_options()
  factory = KonnectFactory(database, identifier, options)

  reactor.listenTCP(1764, factory)
  reactor.listenUDP(0, Discovery(identifier, args.name))
  reactor.listenTCP(8080, Site(API(factory)), interface="127.0.0.1")
  reactor.run()
