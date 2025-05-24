from json import loads
from json.decoder import JSONDecodeError
from logging import debug, error, exception, info, warning
from os import makedirs, remove
from os.path import basename, expanduser, expandvars, getsize, isdir, isfile, join, splitext
from shutil import move
from subprocess import Popen
from tempfile import NamedTemporaryFile
from time import time

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, DatagramProtocol, Protocol
from twisted.internet.reactor import callLater
from twisted.internet.ssl import Certificate
from twisted.protocols.basic import LineReceiver
from twisted.protocols.policies import TimeoutMixin

from konnect.packet import Packet, PacketType


MIN_TCP_PORT = 1716
MAX_TCP_PORT = 1764
DELAY_BETWEEN_PACKETS = 0.5
BUFFER_SIZE = 8192
TIMESTAMP_DIFFERENCE = 1800

NOT_PAIRED = 1
REQUESTED = 2
PAIRED = 3


class Konnect(LineReceiver):
  delimiter = b"\n"
  status = NOT_PAIRED
  identifier = None
  name = "unnamed"
  device = "unknown"
  timeout = None
  commands = {}
  database = None

  def __init__(self):
    self.address = None

  def connectionMade(self):
    self.transport.setTcpKeepAlive(1)
    self.factory.clients.add(self)
    peer = self.transport.getPeer()
    self.address = f"{peer.host}:{peer.port}"
    self.database = self.factory.database

  def connectionLost(self, reason):
    info(f"Device {self.name} disconnected")
    self.factory.clients.remove(self)

  def rawDataReceived(self, data):
    pass

  def _sendPacket(self, data):
    debug(f"SendTCP({self.address}, {self.isSecure()}) - {data}")
    self.sendLine(bytes(data))

  def sendRing(self):
    ring = Packet.createRing()
    self._sendPacket(ring)

  def sendPing(self, msg=None):
    ping = Packet.createPing(msg)
    self._sendPacket(ping)

  def sendNotification(self, text, title, application, reference, payload=None):
    notification = Packet.createNotification(text, title, application, reference, payload)
    self._sendPacket(notification)

  def sendCustom(self, data):
    data["id"] = data.get("id", round(time() * 1000))
    data["body"] = data.get("body", {})

    packet = Packet.load(data)
    self._sendPacket(packet)

  def sendCancel(self, reference):
    cancel = Packet.createCancel(reference)
    self._sendPacket(cancel)

  def sendCommands(self):
    commands = {}

    for row in self.database.listCommands(self.identifier):
      commands[row["key"]] = {"name": row["name"], "command": row["command"]}

    cmd = Packet.createCommands(commands)
    self._sendPacket(cmd)

  def sendRun(self, key):
    cmd = Packet.createRun(key)
    self._sendPacket(cmd)

  def sendPair(self):
    self.status = REQUESTED
    self._cancelTimeout()
    self.timeout = callLater(30, self.sendUnpair)
    pair = Packet.createPair(True)
    self._sendPacket(pair)

  def sendUnpair(self):
    if self.status == REQUESTED:
      info("Pairing request timed out")

    self._cancelTimeout()
    self.status = NOT_PAIRED
    pair = Packet.createPair(False)
    self._sendPacket(pair)
    self.database.unpairDevice(self.identifier)

  def _cancelTimeout(self):
    if self.timeout and self.timeout.active():
      self.timeout.cancel()
      self.timeout = None

  def isTrusted(self):
    return self.database.isDeviceTrusted(self.identifier)

  def _handleIdentity(self, packet):
    self.identifier = packet.get("deviceId")
    self.name = packet.get("deviceName", "unnamed")
    self.device = packet.get("deviceType", "unknown")

    if packet.get("protocolVersion") >= Packet.PROTOCOL_VERSION - 1:
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

    if packet.get("pair"):
      if self.status == REQUESTED:
        info("Pair answer")
        certificate = Certificate(self.transport.getPeerCertificate()).dumpPEM()
        self.status = PAIRED

        if self.isTrusted():
          self.database.updateDevice(self.identifier, self.name, self.device)
        else:
          self.database.pairDevice(self.identifier, certificate, self.name, self.device)
      else:
        info("Pair request")
        pair = Packet.createPair(False)

        if self.status == PAIRED or self.isTrusted():
          info("I'm already paired, but they think I'm not")
          self.database.updateDevice(self.identifier, self.name, self.device)
          pair.set("pair", True)
        else:
          info("Pairing started by the other end, rejecting their request")

        self._sendPacket(pair)
    else:
      info("Unpair request")

      if self.status == REQUESTED:
        info("Canceled by other peer")

      self.status = NOT_PAIRED
      self.database.unpairDevice(self.identifier)

  def _handleNotify(self, packet):
    if packet.get("cancel"):
      reference = packet.get("cancel")
      debug(f"Dismiss notification request for {reference}")
      self.database.dismissNotification(self.identifier, reference)
    elif packet.get("request"):
      info("Registered notifications listener")
      self.database.updateDevice(self.identifier, self.name, self.device)

      for notification in self.database.listNotifications(self.identifier):
        reference = notification["reference"]

        if int(notification["cancel"]):
          text = notification["text"]
          title = notification["title"]
          application = notification["application"]

          callLater(0.1, self.sendNotification, text, title, application, reference)
        else:
          self.sendCancel(reference)
          self.database.dismissNotification(self.identifier, reference)
    else:
      debug("Ignoring unknown request")

  def _handleCommand(self, packet):
    if not packet.get("commandList"):
      return

    try:
      self.commands = loads(packet.get("commandList"))
    except Exception:
      self.commands = {}

  def _handleCommandRequest(self, packet):
    if packet.get("requestCommandList"):
      self.sendCommands()
    elif packet.get("key"):
      key = packet.get("key")
      command = self.database.getCommand(self.identifier, key)

      if not command:
        warning(f"{key} is not a configured command")
      else:
        info(f"Running: {command}")
        Popen([command], shell=True)
    else:  # TODO setup?
      pass

  def _handleShare(self, packet):
    if not packet.get("filename") or not packet.data.get("payloadSize") or \
      not packet.data.get("payloadTransferInfo", {}).get("port"):
      return

    if path := self.database.getPath(self.identifier):
      factory = ClientFactory()
      factory.protocol = ShareReceive
      factory.filename = packet.get("filename")
      factory.payloadSize = packet.data["payloadSize"]
      factory.path = expanduser(expandvars(path))

      reactor.connectSSL(self.transport.getPeer().host, packet.data["payloadTransferInfo"]["port"],
                         factory, self.factory.options)

  def isSecure(self):
    return self.transport.TLS

  def lineReceived(self, line):
    if self.status == NOT_PAIRED and len(line) > BUFFER_SIZE:
      warning(f"Suspiciously long identity package received. Closing connection. {self.address}")
      self.transport.abortConnection()
      return

    try:
      data = loads(line)
      packet = Packet.load(data)
      debug(f"RecvTCP({self.address}, {self.isSecure()}) - {packet}")
    except (JSONDecodeError, TypeError) as e:
      error(f"Unserialization error: {line}")
      exception(e)
      self.transport.abortConnection()
      return

    # if not packet.isValid():
    #   warning("Ignoring malformed packet")
    #   self.transport.abortConnection()
    #   return

    if not self.isSecure():
      if packet.isType(PacketType.IDENTITY):
        self._handleIdentity(packet)
      else:
        warning(f"Device {self.name} not identified, ignoring non encrypted packet {packet.getType()}")
    else:
      identifier = Certificate(self.transport.getPeerCertificate()).getSubject().commonName.decode()

      if self.identifier != identifier:
        warning(f"DeviceID in cert doesn't match deviceID in identity packet. {self.identifier} vs {identifier}")
        self.transport.abortConnection()
      elif packet.isType(PacketType.PAIR):
        self._handlePairing(packet)
      elif packet.isType(PacketType.IDENTITY):  # and packet.get("protocolVersion") == Packet.PROTOCOL_VERSION:
        identity = Packet.createIdentity(self.factory.identifier, self.factory.name,
                                         self.transport.getHost().port, packet.get("protocolVersion"))
        self._sendPacket(identity)
      elif self.isTrusted():
        if packet.isType(PacketType.NOTIFICATION_REQUEST):
          self._handleNotify(packet)
        elif packet.isType(PacketType.PING):
          self.sendPing(packet.get("message"))
        elif packet.isType(PacketType.RUNCOMMAND):
          self._handleCommand(packet)
        elif packet.isType(PacketType.RUNCOMMAND_REQUEST):
          self._handleCommandRequest(packet)
        elif packet.isType(PacketType.SHARE):
          self._handleShare(packet)
        else:
          warning(f"Discarding unsupported packet {packet.getType()} for {self.name}")
      else:
        warning(f"Device {self.name} not paired, ignoring packet {packet.getType()}")
        self.status = NOT_PAIRED
        pair = Packet.createPair(False)
        self._sendPacket(pair)


class Discovery(DatagramProtocol):
  def __init__(self, identifier, name, service_port):
    self.identifier = identifier
    self.name = name
    self.service_port = service_port
    self.last_packets = {}

  def startProtocol(self):
    self.transport.setBroadcastAllowed(True)
    self.announceIdentity()

  def announceIdentity(self, address="<broadcast>", version=None):
    try:
      packet = Packet.createIdentity(self.identifier, self.name, self.service_port, version)
      info("Broadcasting identity packet")
      debug(f"SendUDP({address}:{MIN_TCP_PORT}) - {packet}")
      self.transport.write(bytes(packet), (address, MIN_TCP_PORT))
    except OSError:
      warning("Failed to broadcast identity packet")

  def datagramReceived(self, datagram, addr):
    try:
      data = loads(datagram)
      packet = Packet.load(data)
      debug(f"RecvUDP({addr[0]}:{addr[1]}) - {packet}")
    except (JSONDecodeError, TypeError) as e:
      error(f"Unserialization error: {datagram}")
      exception(e)
      return

    now = time()

    if not packet.isType(PacketType.IDENTITY):
      info(f"Received a UDP packet of wrong type {packet.getType()}")
    elif packet.get("deviceId") == self.identifier:
      debug("Ignoring my own broadcast")
    elif self.last_packets.get(packet.get("deviceId"), 0) + DELAY_BETWEEN_PACKETS > now:
      debug(f"Discarding second UDP packet from the same device {packet.get('deviceId')} received too quickly")
    elif int(packet.get("tcpPort", 0)) < MIN_TCP_PORT or int(packet.get("tcpPort", 0)) > MAX_TCP_PORT:
      debug("TCP port outside of kdeconnect's range")
    elif Packet.PROTOCOL_VERSION - 1 > packet.get("protocolVersion", 0):
      info(f"Refusing to connect to a device using an older protocol version. Ignoring {packet.get('deviceId')}")
    else:
      self.last_packets[packet.get("deviceId")] = now
      debug(f"Received UDP identity packet from {addr[0]}, trying reverse connection")
      self.announceIdentity(addr[0], packet.get("protocolVersion"))


class ShareSend(Protocol, TimeoutMixin):
  def __del__(self):
    callLater(1, self.factory._stopListener, self.factory.port)

  def connectionMade(self):
    address = f"{self.transport.getPeer().host}:{self.transport.getPeer().port}"
    debug(f"Transfer({address}) - File({basename(self.factory.path)}, {getsize(self.factory.path)})")

    with open(self.factory.path, "rb") as f:
      while chunk := f.read(16384):
        self.transport.write(chunk)

    self.setTimeout(1)

  def timeoutConnection(self):
    try:
      self.transport.abortConnection()
    except Exception:
      pass


class ShareReceive(Protocol, TimeoutMixin):
  def connectionMade(self):
    self.tempname = NamedTemporaryFile(delete=False)
    info(f"Receiving file {self.factory.filename}")

  def dataReceived(self, data):
    self.tempname.write(data)

  def connectionLost(self, reason):
    if self.tempname.tell() == self.factory.payloadSize:
      if not isdir(self.factory.path):
        makedirs(self.factory.path, exist_ok=True)

      if path := self.suggestName():
        debug(f"Finished transfer {path}")
        move(self.tempname.name, path)
        return
      else:
        pass  # FIXME
    else:
      warning(f"Received incomplete file ({self.tempname.tell()}/{self.factory.payloadSize} bytes), deleting")

    remove(self.tempname.name)

  def suggestName(self):
    path = join(self.factory.path, self.factory.filename)

    if not isfile(path):
      return path

    debug("Filename already present")
    name, ext = splitext(self.factory.filename)

    for i in range(1, 9999):
      path = join(self.factory.path, f"{name} ({i}){ext}")

      if not isfile(path):
        return path

    return None
