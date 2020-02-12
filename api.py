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

  def _getDeviceId(self, key, value):
    for device in self.konnect.getDevices():
      if device[key] == value:
        return device["identifier"]

    return None

  def render(self, request):
    request.setHeader(b"content-type", b"application/json")
    uri = request.uri.decode()
    method = request.method.decode()
    response, code = self.process(request, method, uri)
    request.setResponseCode(code)
    address = request.getClientAddress()

    if code // 100 == 2 or code // 100 == 3:
      info("%s:%d - %s %s - %d", address.host, address.port, method, uri, code)
    else:
      error("%s:%d - %s %s - %d", address.host, address.port, method, uri, code)

    return dumps(response).encode()

  def process(self, request, method, uri):
    if uri == "/" and method == "GET":
      return self._handleInfo()
    elif uri == "/device" and method == "GET":
      return self._handleDevices()
    elif uri == "/announce" and method == "PUT":
      return self._handleAnnounce()
    else:
      patterns = [r"^\/(?P<resource>ping|notification|device)\/(?P<key>id|name)\/(?P<value>[\w\-.@]+)$",
                  r"^\/(?P<resource>notification)\/(?P<key>id|name)\/(?P<value>[\w\-.@]+)\/(?P<reference>.*)$"]

      for pattern in patterns:
        matches = match(pattern, uri)

        if not matches:
          continue

        identifier = self._getDeviceId(matches.group("key"), matches.group("value"))

        if matches.group("resource") == "ping" and method == "POST":
          return self._handlePing(identifier)
        elif matches.group("resource") == "device":
          if method == "GET":
            return self._handleDevice(identifier)
          elif method == "POST":
            return self._handlePairing(identifier, True)
          elif method == "DELETE":
            return self._handlePairing(identifier, False)
        elif matches.group("resource") == "notification":
          if method == "POST":
            return self._handleNotification(identifier, request.content.read())
          elif method == "DELETE":
            return self._handleCancel(identifier, matches.group("reference"))

    return {"success": False, "message": "invalid request"}, 400

  def _handleInfo(self):
    return {"id": self.konnect.identifier, "name": self.konnect.name, "application": "Konnect " + __version__, "success": True}, 200

  def _handleDevices(self):
    devices = self.konnect.getDevices()
    devices["success"] = True

    return devices, 200

  def _handleAnnounce(self):
    response = {"success": False}
    code = 500

    try:
      self.discovery.broadcastIdentity()
      response["success"] = True
      code = 200
    except Exception:
      response["message"] = "failed to broadcast identity packet"

    return response, code

  def _handlePing(self, identifier):
    response = {"success": False}
    code = 500
    result = self.konnect.sendPing(identifier)

    if result is True:
      response["success"] = True
      code = 200
    elif result is False:
      response["message"] = "device not reachable"
      code = 404
    else:  # if result is None:
      response["message"] = "device not paired"
      code = 401

    return response, code

  def _handleDevice(self, identifier):
    for device in self.konnect.getDevices():
      if device["identifier"] == identifier:
        device["success"] = True
        return device, 200

    return {"success": False, "message": "device not reachable"}, 404

  def _handlePairing(self, identifier, pair):
    response = {"success": False}
    code = 500

    if pair is True:
      result = self.konnect.requestPair(identifier)

      if result is False:
        response["success"] = True
        code = 200
      elif result is True:
        response["message"] = "already paired"
        code = 304
      else:  # if result is None:
        response["message"] = "device not reachable"
        code = 404
    else:
      result = self.konnect.requestUnpair(identifier)

      if result is True:
        response["success"] = True
        code = 200
      elif result is False:
        response["message"] = "device not paired"
        code = 401
      else:  # if result is None:
        response["message"] = "device not reachable"
        code = 404

    return response, code

  def _handleNotification(self, identifier, data):
    response = {"success": False}
    code = 500

    try:
      data = loads(data)

      if "text" not in data or "title" not in data or "application" not in data:
        response["message"] = "text or title or application not found"
        code = 400
      else:
        text = data["text"]
        title = data["title"]
        application = data["application"]
        reference = data.get("reference", "")

        result = self.konnect.sendNotification(identifier, text, title, application, reference)

        if result is True:
          response["success"] = True
          code = 200
        elif result is False:
          response["message"] = "device not reachable"
          code = 404
        else:  # if result is None:
          response["message"] = "device not paired"
          code = 401
    except JSONDecodeError:
      response["message"] = "unserialization error"
      code = 400

    return response, code

  def _handleCancel(self, identifier, reference):
    response = {"success": False}
    code = 500

    result = self.konnect.sendCancel(identifier, reference)

    if result is True:
      response["success"] = True
      code = 200
    elif result is False:
      response["message"] = "device not reachable"
      code = 404
    else:  # if result is None:
      response["message"] = "device not paired"
      code = 401

    return response, code
