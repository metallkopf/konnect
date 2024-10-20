from hashlib import md5
from json import dumps, loads
from json.decoder import JSONDecodeError
from logging import debug, error, info
from os import makedirs
from os.path import getsize, isfile, join
from re import match
from shutil import copyfile, move
from tempfile import gettempdir, mkstemp
from uuid import uuid4

from PIL import Image
from PIL.Image import Resampling
from twisted.internet.address import IPv4Address
from twisted.web.resource import Resource

from konnect import __version__
from konnect.exceptions import ApiError, DeviceNotReachableError, DeviceNotTrustedError, InvalidRequestError, \
  NotImplementedError2, UnserializationError


MAX_ICON_SIZE = 96

FUNCTIONS = {
  # (method, resource): (trusted, reachable)
  # TODO alias, params?
  ("POST", "pair"): (False, True),
  ("DELETE", "pair"): (True, False),
  ("GET", "device"): (True, False),
  ("POST", "ping"): (True, True),
  ("POST", "ring"): (True, True),
  ("POST", "notification"): (True, False),
  ("DELETE", "notification"): (True, False),
  ("POST", "custom"): (True, True),
}


class API(Resource):
  isLeaf = True
  PATTERN = r"^\/(?P<res>[a-z]+)\/(?P<dev>[\w+\.@\- ]+)((?:\/)(?P<id>[\w+\-]+))?$"

  def __init__(self, konnect, discovery, database, debug):
    super().__init__()
    self.konnect = konnect
    self.discovery = discovery
    self.database = database
    self.debug = debug

    self.temp_dir = join(gettempdir(), "konnect_" + konnect.name)
    makedirs(self.temp_dir, exist_ok=True)

  def _getDeviceId(self, item):
    key = "name" if item[0] == "@" else "identifier"
    value = item[1:] if key == "name" else item

    for device in self.konnect.getDevices().values():
      if device[key] == value:
        return device["identifier"]

    return None

  def render(self, request):
    request.setHeader(b"content-type", b"application/json")
    uri = request.uri.decode()
    method = request.method.decode()
    content = request.content.read() if request.getHeader("content-length") else b"{}"

    debug(f"ReqHTTP({method} {uri}) - Body({content})")

    try:
      response, code = self.process(method, uri, content)
      response["success"] = True
    except Exception as e:
      if isinstance(e, ApiError):
        response = {"message": e.args[0]}
        code = e.code

        if e.parent:
          response["exception"] = e.parent
      else:
        response = {"message": "unknown error", "exception": str(e)}
        code = 500

      response["success"] = False

    request.setResponseCode(code)
    address = request.getClientAddress()

    debug(f"RespHTTP({code}) - Body({response})")

    log = info if code // 100 != 5 else error

    if isinstance(address, IPv4Address):
      log(f"{address.host}:{address.port} - {method} {uri} - {code}")
    else:
      log(f"unix:socket - {method} {uri} - {code}")

    return dumps(response).encode()

  def process(self, method, uri, content):
    if uri == "/" and method == "GET":
      return self._handleVersion()
    elif uri == "/" and method == "PUT":
      return self._handleAnnounce()
    elif uri == "/device" and method == "GET":
      return self._handleDevices()

    matches = match(self.PATTERN, uri)

    if not matches:
      raise NotImplementedError2()

    data = {}
    try:
      data = loads(content)
    except JSONDecodeError as e:
      raise UnserializationError(e)

    checks = FUNCTIONS.get((method, matches["res"]))

    if not checks:
      raise NotImplementedError2()

    identifier = self._getDeviceId(matches["dev"])

    if not self.database.isDeviceTrusted(identifier) and checks[0]:
      raise DeviceNotTrustedError()

    client = self.konnect.findClient(identifier)

    if not client and checks[1]:
      raise DeviceNotReachableError()

    name = f"_handle{method.title()}{matches['res'].title()}"

    if not hasattr(self, name):
      raise NotImplementedError2()

    try:
      function = getattr(self, name)
    except AttributeError as e:
      raise NotImplementedError2(e)

    params = [identifier, client]

    if matches["id"]:
      params.append(matches["id"])

    if method in ["POST", "PUT"] and data:
      params.append(data)

    try:
      return function(*params)
    except TypeError as e:
      raise InvalidRequestError(e)

  def _handleVersion(self):
    info = {"id": self.konnect.identifier, "name": self.konnect.name, "application": "Konnect " + __version__}
    return info, 200

  def _handleAnnounce(self):
    try:
      self.discovery.announceIdentity()
      return {}, 204
    except Exception:
      raise ApiError("failed to broadcast identity packet", 500)

  def _handleDevices(self):
    return {"devices": list(self.konnect.getDevices().values())}, 200


  def _handlePostPair(self, identifier, client):
    client.sendPair()
    return {}, 200

  def _handleDeletePair(self, identifier, client):
    self.database.unpairDevice(identifier)
    client.sendUnpair()
    return {}, 200

  def _handleGetDevice(self, identifier, client):
    for device in self.konnect.getDevices().values():
      if device["identifier"] == identifier:
        return device, 200

    raise Exception()

  def _handlePostPing(self, identifier, client):
    client.sendPing()
    return {}, 200

  def _handlePostRing(self, identifier, client):
    client.sendRing()
    return {}, 200

  def _handlePostNotification(self, identifier, client, data):
    if "text" not in data or "title" not in data or "application" not in data:
      raise ApiError("text or title or application not found", 400)

    text = data["text"]
    title = data["title"]
    application = data["application"]
    reference = data.get("reference", "")
    icon = data.get("icon")

    if not isinstance(reference, str) or len(reference) == 0:
      reference = str(uuid4())

    payload = None

    if icon and isfile(icon):
      _, temp = mkstemp()

      with Image.open(icon) as image:
        if image.format != "PNG" or max(image.size) > MAX_ICON_SIZE:
          image.thumbnail([MAX_ICON_SIZE] * 2, Resampling.LANCZOS)
          image.save(temp, "PNG")
        else:
          copyfile(icon, temp)

      with open(temp, "rb") as tmp:
        digest = md5(tmp.read(), usedforsecurity=False).hexdigest()

      path = join(self.temp_dir, digest)
      move(temp, path)

      port = self.konnect.transfer.reservePort(path)

      if port:
        payload = {"digest": digest, "size": getsize(path), "port": port}

    self.database.persistNotification(identifier, text, title, application, reference)

    if client:
      client.sendNotification(text, title, application, reference, payload)

    return {"reference": reference}, 201

  def _handleDeleteNotification(self, identifier, client, reference=None):
    if not reference:
      return {}, 501

    self.database.cancelNotification(identifier, reference)

    if client:
      client.sendCancel(reference)

    return {}, 204

  def _handlePostCustom(self, identifier, client, data):
    if not self.debug:
      raise ApiError("server is not in debug mode", 403)

    if not isinstance(data, dict) or "type" not in data:
      raise ApiError("type not found", 400)

    client.sendCustom(data)
    return {}, 200
