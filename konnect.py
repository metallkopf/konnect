#!/usr/bin/env python3

from twisted.internet import reactor
from twisted.web.server import Site
from os.path import exists
from logging import basicConfig, DEBUG, INFO
from argparse import ArgumentParser
from uuid import uuid4
from protocols import KonnectFactory, Discovery
from api import API
from database import Database
from cert import generate_selfsigned


if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("--name", default="Test")
  parser.add_argument("--debug", action="store_true", default=True)
  args = parser.parse_args()

  level = DEBUG if args.debug else INFO
  basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

  database = Database()
  identifier = database.loadConfig("myself")

  if identifier is None:
    identifier = str(uuid4()).replace("-", "")
    database.saveConfig("myself", identifier)

  generate_selfsigned(identifier)

  factory = KonnectFactory(database, identifier)

  reactor.listenTCP(1764, factory)
  reactor.listenUDP(0, Discovery(identifier, args.name))
  reactor.listenTCP(8080, Site(API(factory)), interface="127.0.0.1")
  reactor.run()
