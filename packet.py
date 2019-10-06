#!/usr/bin/env python3

from time import time
from json import loads, dumps


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
    self.payload = {}
    if _type is None:
      self.payload["id"] = None
    else:
      self.payload["id"] = round(time() * 1000)
    self.payload["type"] = _type
    self.payload["body"] = {}

  def __bytes__(self):
    return dumps(self.payload).encode()

  def __repr__(self):
    return "Packet({{id={d[id]}, type={d[type]}, body={d[body]}}})".format(d=self.payload)

  def set(self, key, value):
    self.payload["body"][key] = value

  def has(self, key):
    return key in self.payload["body"]

  def get(self, key, default=None):
    return self.payload["body"].get(key, default)

  def istype(self, _type):
    return self.payload.get("type") == _type

  @staticmethod
  def createIdentity(identifier, name, port=1764):
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
  def createNotification(text, title="", app="", clearable=False):
    packet = Packet(PacketType.NOTIFICATION)
    packet.set("id", packet.payload["id"])
    packet.set("appName", app)
    packet.set("title", title)
    packet.set("text", text)
    packet.set("isClearable", clearable)

    return packet

  @staticmethod
  def createPing():
    return Packet(PacketType.PING)

  @staticmethod
  def load(payload):
    packet = Packet()
    packet.payload.update(loads(payload))

    return packet
