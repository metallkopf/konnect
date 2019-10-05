#!/usr/bin/env python3

from twisted.internet.protocol import Factory, DatagramProtocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.ssl import Certificate, PrivateCertificate
from logging import debug, info, warning, error
from packet import Packet, PacketType
from database import Database


class InternalStatus:
  NOT_PAIRED = 1
  REQUESTED = 2
  PAIRED = 3

class Konnect(LineReceiver):
  delimiter = b"\n"
  status = InternalStatus.NOT_PAIRED
  notify = False

  def connectionMade(self):
    self.factory.clients.add(self)
    peer = self.transport.getPeer()
    self.address = "{}:{}".format(peer.host, peer.port)

  def connectionLost(self, reason):
    self.factory.clients.remove(self)

  def _sendPacket(self, data):
    debug("SendTo(%s) - %s", self.address, data)
    self.sendLine(bytes(data))

  def sendPing(self):
    ping = Packet.createPing()
    self._sendPacket(ping)

  def sendNotification(self, text, title, app):
    notification = Packet.createNotification(text, title, app)
    self._sendPacket(notification)

  def requestPair(self):
    pair = Packet.createPair(True)
    self._sendPacket(pair)
    self.status = InternalStatus.REQUESTED

  def requestUnpair(self):
    pair = Packet.createPair(False)
    self._sendPacket(pair)
    self.factory.database.unpairDevice(self.identifier)
    self.status = InternalStatus.NOT_PAIRED

  def lineReceived(self, line):
    packet = Packet.load(line)
    debug("RecvFrom(%s) - %s", self.address, packet)

    if not packet.istype(PacketType.IDENTITY) and not self.transport.TLS:
      info("discard non encrypted packet")
      return

    if packet.istype(PacketType.IDENTITY):
      self.identifier = packet.get("deviceId")
      self.name = packet.get("deviceName")
      self.device = packet.get("deviceType")

      if packet.get("protocolVersion") == Packet.PROTOCOL_VERSION:
        info("Starting client ssl (but I'm the server TCP socket)")
        self.transport.startTLS(self.factory.options, False)
        info("Socket succesfully stablished an SSL connection")

        if self.factory.database.isDeviceTrusted(self.identifier):
          info("It is a known device ""%s""" % self.name)
        else:
          info("It is a new device ""%s""" % self.name)
      else:
        info("%s uses an old protocol version, this won't work" % self.name)
        self.transport.abortConnection()
    elif packet.istype(PacketType.PAIR):
      if packet.get("pair") == True:
        if self.factory.database.isDeviceTrusted(self.identifier):
          info("already paired")
          self.requestPair()
          #self.status = InternalStatus.PAIRED
        elif self.status == InternalStatus.REQUESTED:
          debug("pair answer")
          certificate = Certificate(self.transport.getPeerCertificate()).dumpPEM()
          self.factory.database.pairDevice(self.identifier, certificate, self.name, self.device)
          self.status = InternalStatus.PAIRED
        else:
          info("pairing started by the other end, rejecting their request")
          self.requestUnpair()
      else:
        debug("unpair request")
        self.requestUnpair()

        if self.status == InternalStatus.REQUESTED:
          info("canceled by other peer")
    elif packet.istype(PacketType.REQUEST):
      debug("registered notifications listener")

      if self.factory.database.isDeviceTrusted(self.identifier):
        if packet.get("request") == True:
          self.factory.database.updateDevice(self.identifier, self.name, self.device)
          self.notify = True
        else:
          self.notify = False
    elif packet.istype(PacketType.PING):
      self.sendPing()
    else:
      info("discarding unsupported packet")

class KonnectFactory(Factory):
  protocol = Konnect
  clients = set()

  def __init__(self, identifier):
    self.identifier = identifier

  def _findClient(self, identifier):
    for client in self.clients:
      if client.identifier != identifier:
        continue

      return client

    return None

  def sendPing(self, identifier):
    if not self.database.isDeviceTrusted(identifier):
      return None

    try:
      self._findClient(identifier).sendPing()
      return True
    except NoneType:
      return False

  def sendNotification(self, identifier, text, title, app):
    if not self.database.isDeviceTrusted(identifier):
      return None

    try:
      self._findClient(identifier).sendNotification(text, title, app)
      return True
    except NoneType:
      return False

  def requestPair(self, identifier):
    try:
      self._findClient(identifier).requestPair()
      return not self.database.isDeviceTrusted(identifier)
    except NoneType:
      return None

  def isDeviceTrusted(self, identifier):
    return self.database.isDeviceTrusted(identifier)

  def getDevices(self):
    devices = {}

    for trusted in self.database.getTrustedDevices():
      devices[trusted["identifier"]] = {"name": trusted["name"], "type": trusted["type"], "reachable": False, "trusted": True}

    for client in self.clients:
      trusted = client.identifier in devices
      devices[client.identifier] = {"name": client.name, "type": client.device, "reachable": True, "trusted": trusted}

    return devices

  def startFactory(self):
    certificate = open("certificate.pem", "rb").read() + open("privateKey.pem", "rb").read()
    pem = PrivateCertificate.loadPEM(certificate)
    self.options = pem.options()
    self.database = Database(self.identifier)

class Discovery(DatagramProtocol):
  def __init__(self, identifier, device):
    self.identifier = identifier
    self.device = device

  def startProtocol(self):
    self.transport.setBroadcastAllowed(True)
    packet = Packet.createIdentity(self.identifier, self.device)
    info("broadcasting identity packet")
    self.transport.write(bytes(packet), ("<broadcast>", 1716))
    debug(packet)
