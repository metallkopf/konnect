#!/usr/bin/env python3

from twisted.internet.protocol import Factory, DatagramProtocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.ssl import Certificate, PrivateCertificate
from packet import Packet
from database import Database


class Konnect(LineReceiver):
  delimiter = b"\n"
  pairing = False
  secure = False

  def connectionMade(self):
    self.factory.clients.add(self)
    peer = self.transport.getPeer()
    self.address = (peer.host, peer.port)

  def connectionLost(self, reason):
    self.factory.clients.remove(self)

  def _sendPacket(self, data):
    print("sendto", self.address, data)
    self.sendLine(bytes(data))

  def sendPing(self):
    ping = Packet(Packet.PING)
    self._sendPacket(ping)

  def sendNotification(self, text, title, app):
    notification = Packet.create_notification(text, title, app)
    self._sendPacket(notification)

  def lineReceived(self, line):
    packet = Packet.load(line)
    print("recvfrom", self.address, packet)

    if not packet.istype(Packet.IDENTITY) and not self.secure:
      self.transport.abortConnection()

    if packet.istype(Packet.IDENTITY):
      self.identifier = packet.get("deviceId")
      self.name = packet.get("deviceName")
      self.device = packet.get("deviceType")
      self.transport.startTLS(self.factory.options, False)
      self.secure = True

      if not self.factory.database.deviceExists(self.identifier):
        pair = Packet.create_pair(True)
        self._sendPacket(pair)
        self.pairing = True
    elif packet.istype(Packet.PAIR):
      if packet.get("pair") == True:
        if self.pairing:
          print("paired")
          certificate = Certificate(self.transport.getPeerCertificate()).dumpPEM()
          self.factory.database.pairDevice(self.identifier, certificate)
        else:
          print("unpairing")
          pair = Packet.create_pair(False)
          self._sendPacket(pair)
          self.transport.abortConnection()
      else:
        print("unpaired")
        self.factory.database.unpairDevice(self.identifier)
        self.transport.abortConnection()
    elif packet.istype(Packet.REQUEST):
      print("send notifications", packet.get("request"))

      if self.factory.database.deviceExists(self.identifier):
        if packet.get("request") == True:
          self.sendNotification("text", "title", "appName")
      else:
        print("ignore notifications")
    elif packet.istype(Packet.PING):
      self.sendPing()

class KonnectFactory(Factory):
  protocol = Konnect
  clients = set()

  def __init__(self, identifier):
    self.identifier = identifier

  def sendPings(self):
    for client in self.clients:
      client.sendPing()

  def getDevices(self):
    devices = []
    for client in self.clients:
      devices.append({"id": client.identifier, "name": client.name,
                      "type": client.device})
    return devices

  def startFactory(self):
    certificate = open("certificate.pem", "rb").read() + open("privatekey.pem", "rb").read()
    pem = PrivateCertificate.loadPEM(certificate)
    self.options = pem.options()
    self.database = Database(self.identifier)

class Discovery(DatagramProtocol):
  def __init__(self, identifier, device):
    self.identifier = identifier
    self.device = device

  def startProtocol(self):
    self.transport.setBroadcastAllowed(True)
    packet = Packet.create_identity(self.identifier, self.device)
    print(packet)
    self.transport.write(bytes(packet), ("<broadcast>", 1716))
