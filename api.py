#!/usr/bin/env python3

from twisted.web.resource import Resource, NoResource
from json import dumps, loads
from logging import debug, info, warning, error


class API(Resource):
  isLeaf = True

  def __init__(self, konnect):
    super().__init__()
    self.konnect = konnect

  def render(self, request):
    request.setHeader("Content-Type", "application/json")
    address = request.getClientAddress()
    self.client = "{}:{}".format(address.host, address.port)
    info("%s - %s %s", self.client, request.method.decode(), request.uri.decode())

    return super().render(request)

  def render_GET(self, request):
    if request.uri.decode() == "/":
      pass
    elif request.uri.decode() == "/device":
      return dumps(self.konnect.getDevices()).encode()
    else:
      request.setResponseCode(404)

  def render_PUT(self, request):
    command, identifier = request.uri.decode()[1:].split("/", 1)

    if command == "device":
      data = loads(request.content.read())

      if "pair" in data:
        pair = data["pair"]
        response = {"success": False}
        result = self.konnect.requestPair(identifier)

        if result == True:
          response["success"] = True
        elif result == False:
          response["message"] = "already paired"
        elif result is None:
          response["message"] = "device not reachable"

        return dumps(response).encode()
      else:
        request.setResponseCode(400)
    else:
      request.setResponseCode(404)

  def render_POST(self, request):
    command, identifier = request.uri.decode()[1:].split("/", 1)

    if command == "ping":
      result = self.konnect.sendPing(identifier)
      response = {"success": False}

      if result == True:
        response["success"] = True
      elif result == False:
        response["message"] = "device not reachable"
      elif result is None:
        response["message"] = "device not paired"

      return dumps(response).encode()
    elif command == "notify":
      pass
    else:
      request.setResponseCode(404)
