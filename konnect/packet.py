from json import dumps
from re import sub
from time import time
from uuid import uuid4


class PacketType:
  IDENTITY = "kdeconnect.identity"
  NOTIFICATION = "kdeconnect.notification"
  NOTIFICATION_REQUEST = "kdeconnect.notification.request"
  PAIR = "kdeconnect.pair"
  PING = "kdeconnect.ping"
  RING = "kdeconnect.findmyphone.request"
  RUNCOMMAND = "kdeconnect.runcommand"
  RUNCOMMAND_REQUEST = "kdeconnect.runcommand.request"
  SHARE = "kdeconnect.share.request"


class Packet:
  PROTOCOL_VERSION = 8
  DEVICE_TYPE = "desktop"

  def __init__(self, type_=None):
    self.data = {}

    if type_:
      self.data["id"] = round(time() * 1000)
      self.data["type"] = type_
      self.data["body"] = {}

  def __bytes__(self):
    return dumps(self.data).encode()

  def __repr__(self):
    return f"Packet({self.data})"

  def set(self, key, value):
    self.data["body"][key] = value

  def has(self, key):
    return key in self.data["body"]

  def get(self, key, default=None):
    return self.data["body"].get(key, default)

  def isType(self, type_):
    return self.data.get("type") == type_

  def getType(self):
    return self.data.get("type")

  def isValid(self):
    try:
      int(self.data.get("id"))
    except Exception:
      return False

    if not isinstance(self.data.get("body"), dict):
      return False
    elif not self.data.get("type"):
      return False
    elif self.isType(PacketType.IDENTITY):  # tcpPort not sent in tcp identity packet
      return {"deviceId", "deviceName", "deviceType", "protocolVersion", "incomingCapabilities",
              "outgoingCapabilities"}.issubset(self.data["body"].keys())
    elif self.isType(PacketType.PAIR):
      return "pair" in self.data["body"].keys()
    elif self.isType(PacketType.PING) or self.isType(PacketType.RING):
      return True
    elif self.isType(PacketType.NOTIFICATION):
      return True
    else:
      return True  # TODO some other packets

  def filterChars(self, value):
    return sub(r"[^A-Za-z0-9_]", "_", value)

  @staticmethod
  def createIdentity(identifier, name, port, version=None):
    packet = Packet(PacketType.IDENTITY)
    packet.set("protocolVersion", version or Packet.PROTOCOL_VERSION)
    packet.set("deviceId", identifier)
    packet.set("deviceName", name)
    packet.set("deviceType", Packet.DEVICE_TYPE)
    packet.set("tcpPort", port)
    packet.set("incomingCapabilities", [PacketType.PING, PacketType.NOTIFICATION_REQUEST,
                                        PacketType.RUNCOMMAND_REQUEST, PacketType.RUNCOMMAND,
                                        PacketType.SHARE])
    packet.set("outgoingCapabilities", [PacketType.RING, PacketType.NOTIFICATION, PacketType.PING,
                                        PacketType.RUNCOMMAND])

    return packet

  @staticmethod
  def createPair(pairing):
    packet = Packet(PacketType.PAIR)
    packet.set("pair", pairing)
    packet.set("timestamp", round(time()))

    return packet

  @staticmethod
  def createNotification(text, title, application, reference, payload=None):
    packet = Packet(PacketType.NOTIFICATION)
    packet.set("id", reference or str(uuid4()))
    packet.set("appName", application)
    packet.set("title", title)
    packet.set("text", text)
    packet.set("isClearable", True)
    packet.set("ticker", f"{title}: {text}")

    if payload:
      packet.set("payloadHash", payload["digest"])
      packet.data["payloadSize"] = payload["size"]
      packet.data["payloadTransferInfo"] = {"port": payload["port"]}

    return packet

  @staticmethod
  def createCancel(reference):
    packet = Packet(PacketType.NOTIFICATION)
    packet.set("id", reference)
    packet.set("isCancel", True)

    return packet

  @staticmethod
  def createPing(msg=None):
    packet = Packet(PacketType.PING)

    if msg:
      packet.set("message", msg)

    return packet

  @staticmethod
  def createRing():
    return Packet(PacketType.RING)

  @staticmethod
  def createCommands(commands):
    packet = Packet(PacketType.RUNCOMMAND)
    packet.set("canAddCommand", False)
    packet.set("commandList", dumps(commands))

    return packet

  @staticmethod
  def createRun(key):
    packet = Packet(PacketType.RUNCOMMAND_REQUEST)
    packet.set("key", key)

    return packet

  @staticmethod
  def load(data):
    packet = Packet()
    packet.data.update(data)

    return packet
