#!/usr/bin/env python3

from twisted.internet import reactor
from protocols import KonnectFactory, Discovery
from twisted.web.server import Site
from api import API


if __name__ == "__main__":
  identifier = "test"
  device = "Test"

  factory = KonnectFactory(identifier)
  reactor.listenTCP(1764, factory)
  reactor.listenUDP(0, Discovery(identifier, device))
  reactor.listenTCP(8080, Site(API(factory)))
  reactor.run()
