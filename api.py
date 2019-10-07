#!/usr/bin/env python3

from json import dumps, loads
from json.decoder import JSONDecodeError
from logging import info

from twisted.web.resource import Resource


class API(Resource):
  isLeaf = True

  def __init__(self, konnect, discovery):
    super().__init__()
    self.konnect = konnect
    self.discovery = discovery

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
        return dumps({"success": False, "message": "unserialization error"}).encode()

      identifier = self.uri[1:].split("/", 1)[-1]

      if "pair" in data:
        pair = data["pair"]
        response = {"success": False}

        if pair is True:
          result = self.konnect.requestPair(identifier)

          if result is True:
            response["success"] = True
          elif result is False:
            response["message"] = "already paired"
          elif result is None:
            response["message"] = "device not reachable"
        else:
          response = {"success": False}
          result = self.konnect.requestUnpair(identifier)

          if result is True:
            response["success"] = True
          elif result is False:
            response["message"] = "device not paired"
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
    if self.uri == "/broadcast":
      return dumps({"success": self.discovery.broadcastIdentity()}).encode()
    elif self.uri.startswith("/ping/"):
      identifier = self.uri[1:].split("/", 1)[-1]
      result = self.konnect.sendPing(identifier)
      response = {"success": False}

      if result is True:
        response["success"] = True
      elif result is False:
        response["message"] = "device not reachable"
      elif result is None:
        response["message"] = "device not paired"

      return dumps(response).encode()
    elif self.uri.startswith("/notification/"):
      try:
        data = loads(request.content.read())
      except JSONDecodeError:
        request.setResponseCode(400)
        return dumps({"success": False, "message": "unserialization error"}).encode()

      identifier = self.uri[1:].split("/", 1)[-1]

      if "text" not in data or "title" not in data:
        request.setResponseCode(400)
        return b""
      else:
        self.konnect.sendNotification(identifier, data["text"], data["title"], data.get("app", ""))
        #
        return b""
    else:
      request.setResponseCode(404)
      return b""
