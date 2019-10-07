#!/usr/bin/env python3

from argparse import ArgumentParser
from logging import DEBUG, INFO, basicConfig
from platform import node
from uuid import uuid4

from twisted.internet import reactor
from twisted.web.server import Site

from api import API
from certificate import Certificate
from database import Database
from protocols import Discovery, KonnectFactory


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
