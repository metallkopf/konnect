from twisted.internet.protocol import Factory

from konnect.protocols import Konnect


class KonnectFactory(Factory):
  protocol = Konnect
  clients = set()

  def __init__(self, database, identifier, name, options):
    self.database = database
    self.identifier = identifier
    self.name = name
    self.options = options

  def findClient(self, identifier):
    for client in self.clients:
      if client.identifier == identifier:
        return client

    return None

  def getDevices(self):
    devices = self.database.getTrustedDevices()

    for client in self.clients:
      if client.identifier in devices:
        devices[client.identifier]["commands"] = client.commands
        devices[client.identifier]["reachable"] = True
      else:
        devices[client.identifier] = {"identifier": client.identifier, "name": client.name,
                                      "type": client.device, "reachable": True, "trusted": False,
                                      "commands": client.commands, "path": None}

    return devices
