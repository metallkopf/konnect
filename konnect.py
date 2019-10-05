#!/usr/bin/env python3

from twisted.internet import reactor
from twisted.web.server import Site
from os.path import exists
from logging import basicConfig, DEBUG, INFO, info
from protocols import KonnectFactory, Discovery
from api import API
from cert import generate_selfsigned


if __name__ == "__main__":
  basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=DEBUG)

  identifier = "test"
  device = "Test"

  generate_selfsigned(identifier)

  factory = KonnectFactory(identifier)
  reactor.listenTCP(1764, factory)
  reactor.listenUDP(0, Discovery(identifier, device))
  reactor.listenTCP(8080, Site(API(factory)), interface="127.0.0.1")
  reactor.run()
