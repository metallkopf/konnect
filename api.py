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
    response = {}
    code = 200

    if self.uri == "/":
      pass
    elif self.uri == "/device":
      response = self.konnect.getDevices()
    elif self.uri.startswith("/device/"):
      identifier = self.uri[1:].split("/", 1)[-1]
      device = self.konnect.getDevices().get(identifier)

      if device is None:
        code = 404
      else:
        response = device
    else:
      code = 404

    request.setResponseCode(code)
    return dumps(response).encode()

  def _handlePairing(self, identifier, pair):
    response = {"success": False}
    code = 200

    if pair is True:
      result = self.konnect.requestPair(identifier)

      if result is True:
        response["success"] = True
      elif result is False:
        response["message"] = "already paired"
      elif result is None:
        code = 404
        response["message"] = "device not reachable"
    else:
      result = self.konnect.requestUnpair(identifier)

      if result is True:
        response["success"] = True
      elif result is False:
        code = 401
        response["message"] = "device not paired"
      elif result is None:
        code = 404
        response["message"] = "device not reachable"

    return response, code

  def render_PUT(self, request):
    response = {}
    code = 200

    if self.uri.startswith("/device/"):
      try:
        identifier = self.uri[1:].split("/", 1)[-1]
        data = loads(request.content.read())
        pair = bool(data["pair"])

        response, code = self._handlePairing(identifier, pair)
      except IndexError:
        code = 400
        response["message"] = "pair not found"
      except JSONDecodeError:
        code = 400
        response["message"] = "unserialization error"
    else:
      code = 404

    request.setResponseCode(code)
    return dumps(response).encode()

  def _handlePing(self, identifier):
    response = {"success": False}
    code = 200
    result = self.konnect.sendPing(identifier)

    if result is True:
      response["success"] = True
    elif result is False:
      code = 404
      response["message"] = "device not reachable"
    elif result is None:
      code = 401
      response["message"] = "device not paired"

    return response, code

  def _handleNotification(self, identifier, data):
    response = {"success": False}
    code = 200

    if "text" not in data or "title" not in data:
      code = 400
      response["message"] = "text or title not found"
    else:
      text = data["text"]
      title = data["title"]
      application = data.get("appName", "")
      persistent = data.get("persistent", False)

      result = self.konnect.sendNotification(identifier, text, title, application, persistent)

      if result is True:
        response["success"] = True
      elif result is False:
        code = 404
        response["message"] = "device not reachable"
      elif result is None:
        code = 401
        response["message"] = "device not paired"

    return response, code

  def render_POST(self, request):
    response = {}
    code = 200

    if self.uri == "/identity":
      response = {"success": self.discovery.broadcastIdentity()}
    elif self.uri.startswith("/ping/") or self.uri.startswith("/notification/"):
      identifier = self.uri[1:].split("/", 1)[-1]

      if self.uri.startswith("/ping/"):
        response, code = self._handlePing(identifier)
      else:
        try:
          data = loads(request.content.read())
          response, code = self._handleNotification(identifier, data)
        except JSONDecodeError:
          code = 400
          response["message"] = "unserialization error"
    else:
      code = 404

    request.setResponseCode(code)
    return dumps(response).encode()
