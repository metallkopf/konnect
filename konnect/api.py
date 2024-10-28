from hashlib import md5
from json import dumps, loads
from json.decoder import JSONDecodeError
from logging import debug, info
from os import makedirs
from os.path import getsize, isfile, join
from re import match
from shutil import copyfile, move
from tempfile import gettempdir, mkstemp
from traceback import print_exc
from uuid import uuid4

from PIL import Image
from PIL.Image import Resampling
from twisted.internet.address import IPv4Address
from twisted.web.resource import Resource

from konnect import __version__
from konnect.exceptions import ApiError, DeviceNotReachableError, DeviceNotTrustedError, NotImplementedError2, \
  UnserializationError


MAX_ICON_SIZE = 96
CHECKS = {
  # (method, resource): (trusted, reacheable, key)
  ("POST", "pair"): (False, True, False),
  ("DELETE", "pair"): (True, False, False),
  ("GET", "device"): (True, False, False),
  ("POST", "ping"): (True, True, False),
  ("POST", "ring"): (True, True, False),
  ("POST", "notification"): (True, False),
  ("DELETE", "notification"): (True, False, True),
  ("GET", "command"): (True, False, False),
  ("POST", "command"): (True, False, False),
  ("PUT", "command"): (True, False, True),
  ("DELETE", "command"): (True, False, True),
  ("PATCH", "command"): (True, True, True),
  ("POST", "custom"): (True, True, False),
}


class API(Resource):
  isLeaf = True
  PATTERN = r"^\/(?P<res>[a-z]+)\/(?P<dev>[\w+\.@\- ]+)((?:\/)(?P<key>[\w+\-]+))?$"

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
        print_exc()
        response = {"message": "unknown error", "exception": str(e)}
        code = 500

      response["success"] = False

    request.setResponseCode(code)
    address = request.getClientAddress()

    debug(f"RespHTTP({code}) - Body({response})")

    if isinstance(address, IPv4Address):
      info(f"{address.host}:{address.port} - {method} {uri} - {code}")
    else:
      info(f"unix:socket - {method} {uri} - {code}")

    if debug:
      return dumps(response, indent=2).encode() + b"\n"
    else:
      return dumps(response).encode()

  def process(self, method, uri, content):
    if uri == "/" and method == "GET":
      return self._handleInfo()
    elif uri == "/" and method == "PUT":
      return self._handleAnnounce()
    elif uri == "/device" and method == "GET":
      return self._handleDevices()
    elif uri == "/command" and method == "GET":
      return self._handleCommands()
    elif uri == "/notification" and method == "GET":
      return self._handleNotifications()
    elif uri == "/version" and method == "GET":
      return self._handleVersion()

    matches = match(self.PATTERN, uri)

    if not matches:
      raise NotImplementedError2()

    try:
      data = loads(content)
    except JSONDecodeError as e:
      raise UnserializationError(e)

    resource = matches["res"]
    checks = CHECKS.get((method, resource))

    if not checks:
      raise NotImplementedError2()

    identifier = self._getDeviceId(matches["dev"])

    if not self.database.isDeviceTrusted(identifier) and checks[0]:
      raise DeviceNotTrustedError()

    client = self.konnect.findClient(identifier)

    if not client and checks[1]:
      raise DeviceNotReachableError()

    key = matches["key"]

    if key and not checks[2]:
      raise NotImplementedError2()

    if resource == "device" and method == "GET":
      return self._handleGetDevice(identifier)
    elif resource == "pair" and method == "POST":
      return self._handlePair(client)
    elif resource == "pair" and method == "DELETE":
      return self._handleUnpair(identifier, client)
    elif resource == "ping" and method == "POST":
      return self._handlePing(client)
    elif resource == "ring" and method == "POST":
      return self._handleRing(client)
    elif resource == "notification" and method == "POST":
      return self._handleCreateNotification(identifier, client, data)
    elif resource == "notification" and method == "DELETE":
      return self._handleDeleteNotification(identifier, client, key)
    elif resource == "command" and method == "GET":
      return self._handleListCommands(identifier)
    elif resource == "command" and method == "POST":
      return self._handleCreateCommand(identifier, data)
    elif resource == "command" and method == "PUT":
      return self._handleUpdateCommand(identifier, key, data)
    elif resource == "command" and method == "DELETE":
      return self._handleDeleteCommand(identifier, key)
    elif resource == "command" and method == "PATCH":
      return self._handleExecuteCommand(client, key)
    elif resource == "custom" and method == "POST":
      return self._handleCustomPacket(client, data)

    raise NotImplementedError2()

  def _handleInfo(self):
    return {"identifier": self.konnect.identifier, "device": self.konnect.name,
            "server": "Konnect " + __version__}, 200

  def _handleVersion(self):
    return {"version": __version__}, 200

  def _handleAnnounce(self):
    try:
      self.discovery.announceIdentity()
      return {}, 204
    except Exception:
      raise ApiError("failed to broadcast identity packet", 500)

  def _handleDevices(self):
    return {"devices": list(self.konnect.getDevices().values())}, 200

  def _handleCommands(self):
    return {"commands": self.database.listAllCommands()}, 200

  def _handleNotifications(self):
    return {"notifications": self.database.listAllNotifications()}, 200

  def _handlePair(self, client):
    client.sendPair()
    return {}, 200

  def _handleUnpair(self, identifier, client):
    self.database.unpairDevice(identifier)
    client.sendUnpair()
    return {}, 200

  def _handleGetDevice(self, identifier):
    for device in self.konnect.getDevices().values():
      if device["identifier"] == identifier:
        return device, 200

    raise Exception()

  def _handlePing(self, client):
    client.sendPing()
    return {}, 200

  def _handleRing(self, client):
    client.sendRing()
    return {}, 200

  def _handleCreateNotification(self, identifier, client, data):
    if not data.get("text") or not data.get("title") or not data.get("application"):
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

  def _handleListCommands(self, identifier):
    return {"commands": self.database.listCommands(identifier)}, 200

  def _handleCreateCommand(self, identifier, data):
    if not data.get("name") or not data.get("command"):
      raise ApiError("name or command not found", 400)

    key = str(uuid4())
    self.database.addCommand(identifier, key, data["name"], data["command"])
    return {"key": key}, 201

  def _handleUpdateCommand(self, identifier, key, data):
    if not data.get("name") or not data.get("command"):
      raise ApiError("name or command not found", 400)

    if self.database.getCommand(identifier, key):
      self.database.updateCommand(identifier, key, data["name"], data["command"])
      return {}, 200

    raise ApiError("not found", 404)

  def _handleDeleteCommand(self, identifier, key=None):
    if key:
      if self.database.getCommand(identifier, key):
        self.database.remCommand(identifier, key)
      else:
        raise ApiError("not found", 404)
    else:
      self.database.remCommands(identifier)

    return {}, 204

  def _handleExecuteCommand(self, client, key):
    client.sendRun(key)
    return {}, 200

  def _handleCustomPacket(self, client, data):
    if not self.debug:
      raise ApiError("server is not in debug mode", 403)

    if not isinstance(data, dict) or "type" not in data:
      raise ApiError("type not found", 400)

    client.sendCustom(data)
    return {}, 200
