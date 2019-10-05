#!/usr/bin/env python3

from time import time
from json import loads, dumps


class Packet:
  IDENTITY = "kdeconnect.identity"
  PAIR = "kdeconnect.pair"
  NOTIFICATION = "kdeconnect.notification"
  REQUEST = "kdeconnect.notification.request"
  PING = "kdeconnect.ping"

  def __init__(self, _type=None):
    self.payload = {}
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
    return self.payload["type"] == _type

  @staticmethod
  def create_identity(identifier, name="unnamed", device="desktop", port=1764):
    packet = Packet(Packet.IDENTITY)
    packet.set("protocolVersion", 7)
    packet.set("deviceId", identifier)
    packet.set("deviceName", name)
    packet.set("deviceType", device)
    packet.set("tcpPort", port)
    packet.set("incomingCapabilities", [Packet.PING])
    packet.set("outgoingCapabilities", [Packet.NOTIFICATION, Packet.PING])

    return packet

  @staticmethod
  def create_pair(pairing=True):
    packet = Packet(Packet.PAIR)
    packet.set("pair", pairing)

    return packet

  @staticmethod
  def create_notification(text, title="", app="", identifier=None, clearable=False):
    packet = Packet(Packet.NOTIFICATION)
    packet.set("id", identifier if identifier else packet.payload["id"])
    packet.set("appName", app)
    packet.set("title", title)
    packet.set("text", text)
    packet.set("isClearable", clearable)

    return packet

  @staticmethod
  def load(payload):
    packet = Packet()
    packet.payload = loads(payload)

    return packet
