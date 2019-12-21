from json import dumps, loads
from json.decoder import JSONDecodeError
from logging import error, info
from re import match

from twisted.web.resource import Resource

from version import __version__


class API(Resource):
  isLeaf = True

  def __init__(self, konnect, discovery):
    super().__init__()
    self.konnect = konnect
    self.discovery = discovery

  def _getDeviceBy(self, key, value):
    for device in self.konnect.getDevices():
      if device[key] == value:
        return device

    return None

  def render(self, request):
    request.setHeader(b"content-type", b"application/json")
    self.uri = request.uri.decode()
    response = super().render(request)

    address = request.getClientAddress()
    if request.code // 100 == 2:
      info("%s:%d - %s %s - %d", address.host, address.port, request.method.decode(), self.uri, request.code)
    else:
      error("%s:%d - %s %s - %d", address.host, address.port, request.method.decode(), self.uri, request.code)

    return response

  def render_GET(self, request):
    response = {}
    code = 200

    if self.uri == "/":
      response = {"id": self.konnect.identifier, "name": self.konnect.name, "application": "Konnect " + __version__}
    elif self.uri == "/device":
      response = self.konnect.getDevices()
    else:
      matches = match(r"^\/device\/(?P<key>identifier|name)\/(?P<value>[\w\-.@]+)$", self.uri)

      if matches:
        device = self._getDeviceBy(matches.group("key"), matches.group("value"))

        if device is None:
          code = 404
        else:
          response = device
      else:
        code = 400

    request.setResponseCode(code)
    return dumps(response).encode()

  def _handlePairing(self, identifier, data):
    response = {"success": False}
    code = 200

    try:
      data = loads(data)
      pair = bool(data["pair"])

      if pair is True:
        result = self.konnect.requestPair(identifier)

        if result is False:
          response["success"] = True
        elif result is True:
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
    except IndexError:
      code = 400
      response["message"] = "pair not found"
    except JSONDecodeError:
      code = 400
      response["message"] = "unserialization error"

    return response, code

  def render_PUT(self, request):
    response = {}
    code = 200

    matches = match(r"^\/device\/(?P<key>identifier|name)\/(?P<value>[\w\-.@]+)$", self.uri)

    if matches:
      device = self._getDeviceBy(matches.group("key"), matches.group("value"))

      response, code = self._handlePairing(device["identifier"], request.content.read())
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

    try:
      data = loads(data)

      if "text" not in data or "title" not in data or "application" not in data:
        code = 400
        response["message"] = "text or title or application not found"
      else:
        text = data["text"]
        title = data["title"]
        application = data["application"]
        reference = data.get("reference", "")

        result = self.konnect.sendNotification(identifier, text, title, application, reference)

        if result is True:
          response["success"] = True
        elif result is False:
          code = 404
          response["message"] = "device not reachable"
        elif result is None:
          code = 401
          response["message"] = "device not paired"
    except JSONDecodeError:
      code = 400
      response["message"] = "unserialization error"

    return response, code

  def render_POST(self, request):
    response = {"success": False}
    code = 200

    if self.uri == "/identity":
      response = {"success": self.discovery.broadcastIdentity()}
    elif self.uri == "/ping":
      response["success"] = None

      for device in self.konnect.getDevices():
        identifier = device["identifier"]

        if device["reachable"] is True and device["trusted"] is True:
          response[identifier], _ = self._handlePing(identifier)
    elif self.uri == "/notification":
      response["success"] = None

      try:
        data = request.content.read()
        loads(data)

        for device in self.konnect.getDevices():
          identifier = device["identifier"]

          if device["trusted"] is True:
            response[identifier], _ = self._handleNotification(identifier, data)
      except JSONDecodeError:
        code = 400
        response["message"] = "unserialization error"
    else:
      matches = match(r"^\/(?P<resource>ping|notification)\/(?P<key>identifier|name)\/(?P<value>[\w\-.@]+)$", self.uri)

      if matches:
        device = self._getDeviceBy(matches.group("key"), matches.group("value"))

        if matches.group("resource") == "ping":
          response, code = self._handlePing(device["identifier"])
        elif matches.group("resource") == "notification":
          response, code = self._handleNotification(device["identifier"], request.content.read())
        else:
          code = 404
      else:
        code = 400

    request.setResponseCode(code)
    return dumps(response).encode()
