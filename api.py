#!/usr/bin/env python3

from twisted.web.resource import Resource, NoResource
from json import dumps

class API(Resource):
  isLeaf = True

  def __init__(self, konnect):
    super().__init__()
    self.konnect = konnect

  def render_GET(self, request):
    if request.uri.decode() == "/":
      return b"{}"
    elif request.uri.decode() == "/devices":
      return dumps(self.konnect.getDevices())
    elif request.uri.decode() == "/ping":
      self.konnect.sendPings()
      return b"{}"
    else:
      request.setResponseCode(404)
      return b""

  def render_POST(self, request):
    if request.uri.decode() == "/ping":
      self.konnect.sendPings()
      return b"{}"
    else:
      request.setResponseCode(404)
      return b""
