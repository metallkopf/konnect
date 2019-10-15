#!/usr/bin/env python3

from json.decoder import JSONDecodeError
from logging import debug, error, exception, info, warning
from uuid import uuid4

from twisted.internet.protocol import DatagramProtocol, Factory
from twisted.internet.reactor import callLater
from twisted.internet.ssl import Certificate
from twisted.protocols.basic import LineReceiver

from packet import Packet, PacketType


class InternalStatus:
  NOT_PAIRED = 1
  REQUESTED = 2
  PAIRED = 3


class Konnect(LineReceiver):
  delimiter = b"\n"
  status = InternalStatus.NOT_PAIRED
  identifier = None
  name = "unnamed"
  device = "unknown"
  timeout = None

  def connectionMade(self):
    self.transport.setTcpKeepAlive(1)
    self.factory.clients.add(self)
    peer = self.transport.getPeer()
    self.address = "{}:{}".format(peer.host, peer.port)

  def connectionLost(self, reason):
    info("Device %s disconnected", self.name)
    self.factory.clients.remove(self)

  def _sendPacket(self, data):
    debug("SendTo(%s) - %s", self.address, data)
    self.sendLine(bytes(data))

  def sendPing(self):
    ping = Packet.createPing()
    self._sendPacket(ping)

  def sendNotification(self, text, title, application, reference):
    notification = Packet.createNotification(text, title, application, reference)
    self._sendPacket(notification)

  def requestPair(self):
    self.status = InternalStatus.REQUESTED
    self._cancelTimeout()
    self.timeout = callLater(30, self.requestUnpair)
    pair = Packet.createPair(True)
    self._sendPacket(pair)

  def requestUnpair(self):
    if self.status == InternalStatus.REQUESTED:
      info("Pairing request timed out")

    self._cancelTimeout()
    self.status = InternalStatus.NOT_PAIRED
    pair = Packet.createPair(False)
    self._sendPacket(pair)
    self.factory.database.unpairDevice(self.identifier)

  def _cancelTimeout(self):
    if self.timeout is not None and self.timeout.active():
      self.timeout.cancel()
      self.timeout = None

  def isTrusted(self):
    return self.factory.database.isDeviceTrusted(self.identifier)

  def _handleIdentity(self, packet):
    self.identifier = packet.get("deviceId")
    self.name = packet.get("deviceName", "unnamed")
    self.device = packet.get("deviceType", "unknown")

    if packet.get("protocolVersion") == Packet.PROTOCOL_VERSION:
      info("Starting client SSL (but I'm the server TCP socket)")
      self.transport.startTLS(self.factory.options, False)
      info("Socket succesfully established an SSL connection")

      if self.isTrusted():
        info("It is a known device %s", self.name)
      else:
        info("It is a new device %s", self.name)
    else:
      info("%s uses an old protocol version, this won't work", self.name)
      self.transport.abortConnection()

  def _handlePairing(self, packet):
    self._cancelTimeout()

    if packet.get("pair") is True:
      if self.status == InternalStatus.REQUESTED:
        info("Pair answer")
        certificate = Certificate(self.transport.getPeerCertificate()).dumpPEM()
        self.factory.database.pairDevice(self.identifier, certificate, self.name, self.device)
        self.status = InternalStatus.PAIRED
      else:
        info("Pair request")
        pair = Packet.createPair(None)

        if self.status == InternalStatus.PAIRED or self.isTrusted():
          info("I'm already paired, but they think I'm not")
          self.factory.database.updateDevice(self.identifier, self.name, self.device)
          pair.set("pair", True)
        else:
          info("Pairing started by the other end, rejecting their request")
          pair.set("pair", False)

        self._sendPacket(pair)
    else:
      info("Unpair request")

      if self.status == InternalStatus.REQUESTED:
        info("Canceled by other peer")

      self.status = InternalStatus.NOT_PAIRED
      self.factory.database.unpairDevice(self.identifier)

  def _handleNotify(self, packet):
    if packet.get("cancel") is not None:
      reference = packet.get("cancel")
      debug("Dismiss notification request for %s", reference)
      self.factory.database.dismissNotification(self.identifier, reference)
    elif packet.get("request") is True:
      info("Registered notifications listener")
      self.factory.database.updateDevice(self.identifier, self.name, self.device)

      for notification in self.factory.database.showNotifications(self.identifier):
        reference = notification[0]
        text = notification[1]
        title = notification[2]
        application = notification[3]

        self.sendNotification(text, title, application, reference)
    else:
      debug("Ignoring unknown request")

  def lineReceived(self, line):
    try:
      packet = Packet.load(line)
      debug("RecvFrom(%s) - %s", self.address, packet)
    except JSONDecodeError as e:
      error("Unserialization error: %s", line)
      exception(e)
      return

    if not self.transport.TLS:
      if packet.isType(PacketType.IDENTITY):
        self._handleIdentity(packet)
      else:
        warning("Device %s not identified, ignoring non encrypted packet %s", self.name, packet.getType())
    else:
      if packet.isType(PacketType.PAIR):
        self._handlePairing(packet)
      elif self.isTrusted():
        if packet.isType(PacketType.REQUEST):
          self._handleNotify(packet)
        elif packet.isType(PacketType.PING):
          self.sendPing()
        else:
          warning("Discarding unsupported packet %s for %s", packet.getType(), self.name)
      else:
        warning("Device %s not paired, ignoring packet %s", self.name, packet.getType())
        self.status = InternalStatus.NOT_PAIRED
        pair = Packet.createPair(False)
        self._sendPacket(pair)


class KonnectFactory(Factory):
  protocol = Konnect
  clients = set()

  def __init__(self, database, identifier, options):
    self.database = database
    self.identifier = identifier
    self.options = options

  def _findClient(self, identifier):
    for client in self.clients:
      if client.identifier == identifier:
        return client

    return None

  def sendPing(self, identifier):
    if not self.isDeviceTrusted(identifier):
      return None

    try:
      self._findClient(identifier).sendPing()
      return True
    except AttributeError:
      return False

  def sendNotification(self, identifier, text, title, application, reference):
    if not self.isDeviceTrusted(identifier):
      return None

    try:
      client = self._findClient(identifier)

      if not isinstance(reference, str) or len(reference) == 0:
        reference = str(uuid4())

      self.database.persistNotification(identifier, text, title, application, reference)
      client.sendNotification(text, title, application, reference)

      return True
    except AttributeError:
      return False

  def requestPair(self, identifier):
    try:
      self._findClient(identifier).requestPair()
      return self.isDeviceTrusted(identifier)
    except AttributeError:
      return None

  def requestUnpair(self, identifier):
    try:
      trusted = self.isDeviceTrusted(identifier)
      self._findClient(identifier).requestUnpair()
      return trusted
    except AttributeError:
      return None

  def isDeviceTrusted(self, identifier):
    return self.database.isDeviceTrusted(identifier)

  def getDevices(self):
    devices = {}

    for trusted in self.database.getTrustedDevices():
      devices[trusted[0]] = {"name": trusted[1], "type": trusted[2], "reachable": False, "trusted": True}

    for client in self.clients:
      trusted = client.identifier in devices
      devices[client.identifier] = {"name": client.name, "type": client.device, "reachable": True, "trusted": trusted}

    return devices


class Discovery(DatagramProtocol):
  def __init__(self, identifier, name, discovery_port, service_port):
    self.identifier = identifier
    self.name = name
    self.port = discovery_port
    self.packet = Packet.createIdentity(self.identifier, self.name, service_port)

  def startProtocol(self):
    self.transport.setBroadcastAllowed(True)
    self.broadcastIdentity()

  def broadcastIdentity(self, address="<broadcast>"):
    try:
      info("Broadcasting identity packet")
      debug("SendTo(%s:%d) - %s", address, self.port, self.packet)
      self.transport.write(bytes(self.packet), (address, self.port))
    except OSError:
      warning("Failed to broadcast identity packet")

  def datagramReceived(self, datagram, addr):
    try:
      packet = Packet.load(datagram)
      debug("RecvFrom(%s:%d) - %s", addr[0], addr[1], packet)
    except JSONDecodeError as e:
      error("Unserialization error: %s", datagram)
      exception(e)
      return

    if not packet.isType(PacketType.IDENTITY):
      info("Received a UDP packet of wrong type %s", packet.getType())
    elif packet.get("deviceId") == self.identifier:
      debug("Ignoring my own broadcast")
    else:
      debug("Received UDP identity packet from %s, trying reverse connection", addr[0])
      self.broadcastIdentity(addr[0])
