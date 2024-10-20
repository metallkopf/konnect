from twisted.internet.protocol import Factory

from konnect.protocols import FileTransfer, Konnect


class KonnectFactory(Factory):
  protocol = Konnect
  clients = set()

  def __init__(self, database, identifier, name, options, transfer):
    self.database = database
    self.identifier = identifier
    self.name = name
    self.options = options
    self.transfer = transfer

  def buildProtocol(self, addr):
    proto = super().buildProtocol(addr)
    proto.database = self.database

    return proto

  def findClient(self, identifier):
    for client in self.clients:
      if client.identifier == identifier:
        return client

    return None

  def getDevices(self):
    devices = {}

    for trusted in self.database.getTrustedDevices():
      devices[trusted[0]] = {"identifier": trusted[0], "name": trusted[1], "type": trusted[2],
                             "reachable": False, "trusted": True, "commands": {}}

    for client in self.clients:
      trusted = client.identifier in devices
      devices[client.identifier] = {"identifier": client.identifier, "name": client.name,
                                    "type": client.device, "reachable": True, "trusted": trusted,
                                    "commands": client.commands}

    return devices


class TransferFactory(Factory):
  protocol = FileTransfer
  jobs = {}

  def __init__(self, top_port, total):
    for x in range(total):
      self.jobs[top_port - x] = None

  def reservePort(self, path):
    for port, path2 in self.jobs.items():

      if not path2:
        self.jobs[port] = path
        return port

    return None
