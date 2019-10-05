#!/usr/bin/env python3

from sqlite3 import connect, OperationalError


class Database:
  def __init__(self, identifier):
    self.instance = connect("konnect.db", isolation_level=None)
    self._upgradeSchema(identifier)

  def _upgradeSchema(self, identifier):
    version = 0

    try:
      query = "SELECT value FROM config WHERE key = ? LIMIT 1"
      version = int(self.instance.execute(query, ("schema", )).fetchone()[0])
    except (OperationalError, TypeError) as e:
      pass

    if version == 0:
      query = "CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)"
      self.instance.execute(query)

      query = "INSERT INTO config VALUES (?, ?)"
      self.instance.execute(query, ("schema", "1"))

      query = "INSERT INTO config VALUES (?, ?)"
      self.instance.execute(query, ("myself", identifier))

      query = "CREATE TABLE trusted_devices (identifier TEXT PRIMARY KEY, certificate TEXT)"
      self.instance.execute(query)
    else:
      query = "UPDATE config SET value = ? WHERE key = ?"
      self.instance.execute(query, (identifier, "myself"))

  def deviceExists(self, identifier):
    query = "SELECT COUNT(1) FROM trusted_devices WHERE identifier = ?"
    return bool(self.instance.execute(query, (identifier, )).fetchone()[0])

  def pairDevice(self, identifier, certificate):
    query = "INSERT INTO trusted_devices (identifier, certificate) VALUES (?, ?)"
    self.instance.execute(query, (identifier, certificate))

  def unpairDevice(self, identifier):
    query = "DELETE FROM trusted_devices WHERE identifier = ?"
    self.instance.execute(query, (identifier, ))
