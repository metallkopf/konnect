#!/usr/bin/env python3

from os.path import join
from sqlite3 import OperationalError, Row, connect


class Database:
  SCHEMA_VERSION = 2

  def __init__(self, path):
    self.instance = connect(join(path, "konnect.db"), isolation_level=None, check_same_thread=False)
    self.instance.row_factory = Row

    version = int(self.loadConfig("schema", 0))

    if version != Database.SCHEMA_VERSION:
      self._upgradeSchema(version)

  def _upgradeSchema(self, version):
    if version == 0:
      version += 1
      queries = ["CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)",
                 "CREATE TABLE trusted_devices (identifier TEXT PRIMARY KEY, certificate TEXT)",
                 "ALTER TABLE trusted_devices ADD COLUMN name TEXT",
                 "ALTER TABLE trusted_devices ADD COLUMN type TEXT"]
      for query in queries:
        self.instance.execute(query)

    if version == 1:
      version += 1
      queries = ["CREATE TABLE notifications (id INTEGER PRIMARY KEY, identifier TEXT, [text] TEXT, title TEXT, application TEXT)",
                 "CREATE INDEX notification_identifier ON notifications (identifier)"]
      for query in queries:
        self.instance.execute(query)

    self.saveConfig("schema", version)

  def loadConfig(self, key, default=None):
    try:
      query = "SELECT value FROM config WHERE key = ?"
      return self.instance.execute(query, (key,)).fetchone()[0]
    except (OperationalError, TypeError):
      return default

  def saveConfig(self, key, value):
    query = "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value"
    self.instance.execute(query, (key, value))

  def isDeviceTrusted(self, identifier):
    query = "SELECT COUNT(1) FROM trusted_devices WHERE identifier = ?"
    return bool(self.instance.execute(query, (identifier,)).fetchone()[0])

  def getTrustedDevices(self):
    query = "SELECT identifier, name, type FROM trusted_devices"
    return self.instance.execute(query).fetchall()

  def updateDevice(self, identifier, name, device):
    query = "UPDATE trusted_devices SET name = ?, type = ? WHERE identifier = ?"
    self.instance.execute(query, (name, device, identifier))

  def pairDevice(self, identifier, certificate, name, device):
    query = "INSERT INTO trusted_devices (identifier, certificate, name, type) VALUES (?, ?, ?, ?) "\
      "ON CONFLICT(identifier) DO UPDATE SET certificate = excluded.certificate, name = excluded.name, type = excluded.type"
    self.instance.execute(query, (identifier, certificate, name, device))

  def unpairDevice(self, identifier):
    query = "DELETE FROM trusted_devices WHERE identifier = ?"
    self.instance.execute(query, (identifier,))

  def createNotification(self, identifier, text, title, application):
    query = "INSERT INTO notifications (identifier, [text], title, application) VALUES (?, ?, ?, ?)"
    self.instance.execute(query, (identifier, text, title, application))

  def dismissNotification(self, _id):
    query = "DELETE FROM notifications WHERE id = ?"
    self.instance.execute(query, (_id,))

  def showNotifications(self, identifier):
    query = "SELECT * FROM notifications WHERE identifier = ?"
    return self.instance.execute(query, (identifier,)).fetchall()
