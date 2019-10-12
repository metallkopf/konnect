#!/usr/bin/env python3

from json import dumps, loads
from time import time
from uuid import uuid4


class PacketType:
  IDENTITY = "kdeconnect.identity"
  PAIR = "kdeconnect.pair"
  NOTIFICATION = "kdeconnect.notification"
  REQUEST = "kdeconnect.notification.request"
  PING = "kdeconnect.ping"


class Packet:
  PROTOCOL_VERSION = 7
  DEVICE_TYPE = "desktop"

  def __init__(self, _type=None):
    self.data = {}
    self.data["id"] = None if _type is None else round(time() * 1000)
    self.data["type"] = _type
    self.data["body"] = {}

  def __bytes__(self):
    return dumps(self.data).encode()

  def __repr__(self):
    return "Packet({{id={d[id]}, type={d[type]}, body={d[body]}}})".format(d=self.data)

  def set(self, key, value):
    self.data["body"][key] = value

  def has(self, key):
    return key in self.data["body"]

  def get(self, key, default=None):
    return self.data["body"].get(key, default)

  def isType(self, _type):
    return self.data.get("type") == _type

  def getType(self):
    return self.data.get("type")

  @staticmethod
  def createIdentity(identifier, name, port):
    packet = Packet(PacketType.IDENTITY)
    packet.set("protocolVersion", Packet.PROTOCOL_VERSION)
    packet.set("deviceId", identifier)
    packet.set("deviceName", name)
    packet.set("deviceType", Packet.DEVICE_TYPE)
    packet.set("tcpPort", port)
    packet.set("incomingCapabilities", [PacketType.PING])
    packet.set("outgoingCapabilities", [PacketType.NOTIFICATION, PacketType.PING])

    return packet

  @staticmethod
  def createPair(pairing):
    packet = Packet(PacketType.PAIR)
    packet.set("pair", pairing)

    return packet

  @staticmethod
  def createNotification(text, title="", application="", reference=None):
    packet = Packet(PacketType.NOTIFICATION)
    packet.set("id", reference or str(uuid4()))
    packet.set("appName", application)
    packet.set("title", title)
    packet.set("text", text)
    packet.set("isClearable", True)
    packet.set("ticker", "%s: %s" % (title, text))

    return packet

  @staticmethod
  def createPing():
    return Packet(PacketType.PING)

  @staticmethod
  def load(data):
    packet = Packet()
    packet.data.update(loads(data))

    return packet
