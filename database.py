#!/usr/bin/env python3

from sqlite3 import connect, OperationalError, Row


class Database:
  def __init__(self, identifier):
    self.instance = connect("konnect.db", isolation_level=None, check_same_thread=False)
    self.instance.row_factory = Row
    self._upgradeSchema(identifier)

  def _upgradeSchema(self, identifier):
    version = 0

    try:
      query = "SELECT value FROM config WHERE key = ? LIMIT 1"
      version = int(self.instance.execute(query, ("schema", )).fetchone()[0])
    except (OperationalError, TypeError) as e:
      pass

    if version == 0:
      version = 1

      query = "CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)"
      self.instance.execute(query)

      query = "INSERT INTO config VALUES (?, ?)"
      self.instance.execute(query, ("schema", "1"))

      query = "INSERT INTO config VALUES (?, ?)"
      self.instance.execute(query, ("myself", identifier))

      query = "CREATE TABLE trusted_devices (identifier TEXT PRIMARY KEY, certificate TEXT)"
      self.instance.execute(query)


    if version == 1:
      version = 2

      queries = ["ALTER TABLE trusted_devices ADD COLUMN name TEXT",
                 "ALTER TABLE trusted_devices ADD COLUMN type TEXT"]
      for query in queries:
        self.instance.execute(query)

      query = "UPDATE config SET value = ? WHERE key = ?"
      self.instance.execute(query, ("schema", "2"))


    query = "UPDATE config SET value = ? WHERE key = ?"
    self.instance.execute(query, (identifier, "myself"))

  def isDeviceTrusted(self, identifier):
    query = "SELECT COUNT(1) FROM trusted_devices WHERE identifier = ?"
    return bool(self.instance.execute(query, (identifier, )).fetchone()[0])

  def getTrustedDevices(self):
    query = "SELECT identifier, name, type FROM trusted_devices"
    return self.instance.execute(query).fetchall()

  def updateDevice(self, identifier, name="unnamed", device="unknown"):
    query = "UPDATE trusted_devices SET name = ?, type = ? WHERE identifier = ?"
    self.instance.execute(query, (name, device, identifier))

  def pairDevice(self, identifier, certificate, name="unnamed", device="unknown"):
    query = "INSERT INTO trusted_devices (identifier, certificate, name, type) VALUES (?, ?, ?, ?)"
    self.instance.execute(query, (identifier, certificate, name, device))

  def unpairDevice(self, identifier):
    query = "DELETE FROM trusted_devices WHERE identifier = ?"
    self.instance.execute(query, (identifier, ))
