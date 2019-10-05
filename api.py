#!/usr/bin/env python3

from twisted.web.resource import Resource
from json import dumps, loads
from json.decoder import JSONDecodeError
from logging import debug, info, warning, error


class API(Resource):
  isLeaf = True

  def __init__(self, konnect):
    super().__init__()
    self.konnect = konnect

  def render(self, request):
    request.setHeader(b"content-type", b"application/json")
    address = request.getClientAddress()
    self.client = "{}:{}".format(address.host, address.port)
    self.uri = request.uri.decode()
    info("%s - %s %s", self.client, request.method.decode(), self.uri)

    return super().render(request)

  def render_GET(self, request):
    if self.uri == "/":
      return b""
    elif self.uri == "/device":
      return dumps(self.konnect.getDevices()).encode()
    elif self.uri.startswith("/device/"):
      identifier = self.uri[1:].split("/", 1)[-1]
      device = self.konnect.getDevices().get(identifier)

      if device is None:
        request.setResponseCode(404)
        return b""
      else:
        return dumps(device).encode()
    else:
      request.setResponseCode(404)
      return b""

  def render_PUT(self, request):
    if self.uri.startswith("/device/"):
      try:
        data = loads(request.content.read())
      except JSONDecodeError:
        request.setResponseCode(400)
        return b""

      identifier = self.uri[1:].split("/", 1)[-1]

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
        return b""
    else:
      request.setResponseCode(404)
      return b""

  def render_POST(self, request):
    if self.uri.startswith("/ping/"):
      identifier = self.uri[1:].split("/", 1)[-1]
      result = self.konnect.sendPing(identifier)
      response = {"success": False}

      if result == True:
        response["success"] = True
      elif result == False:
        response["message"] = "device not reachable"
      elif result is None:
        response["message"] = "device not paired"

      return dumps(response).encode()
    elif self.uri.startswith("/notification/"):
      try:
        data = loads(request.content.read())
      except JSONDecodeError:
        request.setResponseCode(400)
        return b""

      identifier = self.uri[1:].split("/", 1)[-1]

      if ["text", "title"] not in data:
        request.setResponseCode(400)
        return b""
      else:
        self.konnect.sendNotification(identifier, data["text"], data["title"], data.get("app"))
        #
    else:
      request.setResponseCode(404)
      return b""
