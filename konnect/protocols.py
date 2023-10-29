from hashlib import md5
from io import BytesIO
from json.decoder import JSONDecodeError
from logging import debug, error, exception, info, warning
from os import makedirs
from os.path import basename, getsize, join
from shutil import move
from tempfile import gettempdir, mkstemp
from uuid import uuid4

from PIL import Image
from PIL.Image import Resampling
from twisted.internet.protocol import DatagramProtocol, Factory, Protocol
from twisted.internet.reactor import callLater
from twisted.internet.ssl import Certificate
from twisted.protocols.basic import LineReceiver
from twisted.protocols.policies import TimeoutMixin

from konnect.packet import Packet, PacketType


MAX_ICON_SIZE = 128


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
    self.address = f"{peer.host}:{peer.port}"

  def connectionLost(self, reason):
    info(f"Device {self.name} disconnected")
    self.factory.clients.remove(self)

  def _sendPacket(self, data):
    debug(f"SendTo({self.address}) - {data}")
    self.sendLine(bytes(data))

  def sendRing(self):
    ring = Packet.createRing()
    self._sendPacket(ring)

  def sendPing(self):
    ping = Packet.createPing()
    self._sendPacket(ping)

  def sendNotification(self, text, title, application, reference, payload=None):
    notification = Packet.createNotification(text, title, application, reference, payload)
    self._sendPacket(notification)

  def sendCancel(self, reference):
    cancel = Packet.createCancel(reference)
    self._sendPacket(cancel)

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
        info(f"It is a known device {self.name}")
      else:
        info(f"It is a new device {self.name}")
    else:
      info(f"{self.name} uses an old protocol version, this won't work")
      self.transport.abortConnection()

  def _handlePairing(self, packet):
    self._cancelTimeout()

    if packet.get("pair") is True:
      if self.status == InternalStatus.REQUESTED:
        info("Pair answer")
        certificate = Certificate(self.transport.getPeerCertificate()).dumpPEM()
        self.status = InternalStatus.PAIRED

        if self.isTrusted():
          self.factory.database.updateDevice(self.identifier, self.name, self.device)
        else:
          self.factory.database.pairDevice(self.identifier, certificate, self.name, self.device)
      else:
        info("Pair request")
        pair = Packet.createPair(False)

        if self.status == InternalStatus.PAIRED or self.isTrusted():
          info("I'm already paired, but they think I'm not")
          self.factory.database.updateDevice(self.identifier, self.name, self.device)
          pair.set("pair", True)
        else:
          info("Pairing started by the other end, rejecting their request")

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
      debug(f"Dismiss notification request for {reference}")
      self.factory.database.dismissNotification(self.identifier, reference)
    elif packet.get("request") is True:
      info("Registered notifications listener")
      self.factory.database.updateDevice(self.identifier, self.name, self.device)

      for notification in self.factory.database.showNotifications(self.identifier):
        cancel = int(notification[0])
        reference = notification[1]

        if cancel == 0:
          text = notification[2]
          title = notification[3]
          application = notification[4]

          self.sendNotification(text, title, application, reference)
        else:
          self.sendCancel(reference)
          self.factory.database.dismissNotification(self.identifier, reference)
    else:
      debug("Ignoring unknown request")

  def lineReceived(self, line):
    try:
      packet = Packet.load(line)
      debug(f"RecvFrom({self.address}) - {packet}")
    except JSONDecodeError as e:
      error(f"Unserialization error: {line}")
      exception(e)
      return

    if not self.transport.TLS:
      if packet.isType(PacketType.IDENTITY):
        self._handleIdentity(packet)
      else:
        warning(f"Device {self.name} not identified, ignoring non encrypted packet {packet.getType()}")
    else:
      if packet.isType(PacketType.PAIR):
        self._handlePairing(packet)
      elif self.isTrusted():
        if packet.isType(PacketType.REQUEST):
          self._handleNotify(packet)
        elif packet.isType(PacketType.PING):
          self.sendPing()
        else:
          warning(f"Discarding unsupported packet {packet.getType()} for {self.name}")
      else:
        warning(f"Device {self.name} not paired, ignoring packet {packet.getType()}")
        self.status = InternalStatus.NOT_PAIRED
        pair = Packet.createPair(False)
        self._sendPacket(pair)


class KonnectFactory(Factory):
  protocol = Konnect
  clients = set()

  def __init__(self, database, identifier, name, options, transfer):
    self.database = database
    self.identifier = identifier
    self.name = name
    self.options = options
    self.transfer = transfer

    self.temp_dir = join(gettempdir(), "konnect_" + name)
    makedirs(self.temp_dir, exist_ok=True)

  def _findClient(self, identifier):
    for client in self.clients:
      if client.identifier == identifier:
        return client

    return None

  def sendRing(self, identifier):
    if not self.isDeviceTrusted(identifier):
      return None

    try:
      self._findClient(identifier).sendRing()

      return True
    except AttributeError:
      return False

  def sendPing(self, identifier):
    if not self.isDeviceTrusted(identifier):
      return None

    try:
      self._findClient(identifier).sendPing()

      return True
    except AttributeError:
      return False

  def sendNotification(self, identifier, text, title, application, reference, icon=None):
    if not self.isDeviceTrusted(identifier):
      return None

    try:
      client = self._findClient(identifier)

      if not isinstance(reference, str) or len(reference) == 0:
        reference = str(uuid4())

      payload = None

      if icon:
        _, temp = mkstemp()

        with Image.open(BytesIO(icon)) as image:
          image.thumbnail([MAX_ICON_SIZE] * 2, Resampling.LANCZOS)
          image.save(temp, "PNG")

        digest = md5(open(temp, "rb").read()).hexdigest()
        path = join(self.temp_dir, digest)
        move(temp, path)

        size = getsize(path)
        port = self.transfer.reservePort(path)

        if port:
          payload = {"digest": digest, "size": size, "port": port}

      self.database.persistNotification(identifier, text, title, application, reference)
      client.sendNotification(text, title, application, reference, payload)

      return True
    except AttributeError:
      return False

  def sendCancel(self, identifier, reference):
    if not self.isDeviceTrusted(identifier):
      return None

    try:
      self._findClient(identifier).sendCancel(reference)

      return True
    except AttributeError:
      self.database.cancelNotification(identifier, reference)

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
      devices[trusted[0]] = {"identifier": trusted[0], "name": trusted[1], "type": trusted[2], "reachable": False, "trusted": True}

    for client in self.clients:
      trusted = client.identifier in devices
      devices[client.identifier] = {"identifier": client.identifier, "name": client.name, "type": client.device, "reachable": True, "trusted": trusted}

    return devices


class Discovery(DatagramProtocol):
  def __init__(self, identifier, name, discovery_port, service_port):
    self.identifier = identifier
    self.name = name
    self.port = discovery_port
    self.packet = Packet.createIdentity(self.identifier, self.name, service_port)

  def startProtocol(self):
    self.transport.setBroadcastAllowed(True)
    self.announceIdentity()

  def announceIdentity(self, address="<broadcast>"):
    try:
      info("Broadcasting identity packet")
      debug(f"SendTo({address}:{self.port}) - {self.packet}")
      self.transport.write(bytes(self.packet), (address, self.port))
    except OSError:
      warning("Failed to broadcast identity packet")

  def datagramReceived(self, datagram, addr):
    try:
      packet = Packet.load(datagram)
      debug(f"RecvFrom({addr[0]}:{addr[1]}) - {packet}")
    except JSONDecodeError as e:
      error(f"Unserialization error: {datagram}")
      exception(e)
      return

    if not packet.isType(PacketType.IDENTITY):
      info(f"Received a UDP packet of wrong type {packet.getType()}")
    elif packet.get("deviceId") == self.identifier:
      debug("Ignoring my own broadcast")
    else:
      debug(f"Received UDP identity packet from {addr[0]}, trying reverse connection")
      self.announceIdentity(addr[0])


class FileTransfer(Protocol, TimeoutMixin):
  def connectionMade(self):
    self.transport.setTcpNoDelay(True)
    self.transport.setTcpKeepAlive(0)
    peer = self.transport.getPeer()
    self.address = f"{peer.host}:{peer.port}"
    self.port = self.transport.getHost().port

    self.sendFile()

  def sendFile(self):
    path = self.factory.jobs.get(self.port, "")
    debug(f"Transfer({self.address}) - File({basename(path)})")

    if not path:
      self.setTimeout(0)
      return

    with open(path, "rb") as handle:
      while True:
        chunk = handle.read(2048)

        if not chunk:
          break

        self.transport.write(chunk)

    self.setTimeout(1)

  def timeoutConnection(self):
    self.transport.abortConnection()

  def connectionLost(self, reason):
    self.setTimeout(None)
    self.factory.jobs[self.port] = None


class TransferFactory(Factory):
  protocol = FileTransfer
  jobs = {}

  def __init__(self, top_port, total):
    for x in range(total):
      self.jobs[top_port - x] = None

  def reservePort(self, path):
    for port, path2 in self.jobs.items():
      if path2:
        continue

      self.jobs[port] = path
      return port

    return None
