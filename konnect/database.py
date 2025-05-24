from logging import debug
from sqlite3 import OperationalError, connect


class Database:
  SCHEMA = [
    [
      "CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)",
      "CREATE TABLE trusted_devices (identifier TEXT PRIMARY KEY, certificate TEXT, name TEXT, type TEXT)",
      "CREATE TABLE notifications (reference TEXT, identifier TEXT, [text] TEXT, "
      "title TEXT, application TEXT, PRIMARY KEY (identifier, reference), "
      "FOREIGN KEY (identifier) REFERENCES trusted_devices (identifier) ON DELETE CASCADE)",
      "CREATE INDEX notification_identifier ON notifications (identifier)",
    ],
    [
      "ALTER TABLE notifications ADD COLUMN cancel INTEGER DEFAULT 0",
    ],
    [
      "CREATE TABLE commands (key TEXT PRIMARY KEY, identifier TEXT, name TEXT, command TEXT, "
      "FOREIGN KEY (identifier) REFERENCES trusted_devices (identifier) ON DELETE CASCADE)",
    ],
    [
      "ALTER TABLE trusted_devices ADD COLUMN path TEXT",
    ],
  ]

  def __init__(self, path):
    self.instance = connect(path, isolation_level=None, check_same_thread=False)
    self.instance.row_factory = self._dict_factory
    self._upgradeSchema()

  def _dict_factory(self, cursor, row):
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))

  def _execute(self, query, params=()):
    debug(f"Query({query}) - Params({params})")
    result = self.instance.execute(query, params)
    keyword = query.split(" ", 1)[0].upper()

    if keyword == "SELECT":
      result = result.fetchall()
      debug(f"Result({result})")
    elif keyword == "INSERT":
      result = result.lastrowid
      debug(f"LastRowId({result})")
    elif keyword in ["UPDATE", "DELETE"]:
      result = result.rowcount
      debug(f"RowCount({result})")

    return result

  def _upgradeSchema(self):
    version = int(self.loadConfig("schema", -1))

    for index, queries in enumerate(self.SCHEMA):
      if index > version:
        version = index

        for query in queries:
          self._execute(query)

    self.saveConfig("schema", version)

  def loadConfig(self, key, default=None):
    try:
      query = "SELECT value FROM config WHERE key = ?"
      return self._execute(query, (key,))[0]["value"]
    except (OperationalError, TypeError):
      return default

  def saveConfig(self, key, value):
    query = "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value"
    self._execute(query, (key, value))

  def isDeviceTrusted(self, identifier):
    query = "SELECT COUNT(1) AS count FROM trusted_devices WHERE identifier = ?"
    try:
      return int(self._execute(query, (identifier,))[0]["count"]) == 1
    except IndexError:
      return False

  def getTrustedDevices(self):
    query = "SELECT identifier, name, type, path FROM trusted_devices"
    items = {}

    for row in self._execute(query):
      items[row["identifier"]] = {"identifier": row["identifier"], "name": row["name"], "type": row["type"],
                                  "reachable": False, "trusted": True, "commands": {}, "path": row["path"]}

    return items

  def updateDevice(self, identifier, name, device):
    query = "UPDATE trusted_devices SET name = ?, type = ? WHERE identifier = ?"
    self._execute(query, (name, device, identifier))

  def pairDevice(self, identifier, certificate, name, device):
    query = "INSERT INTO trusted_devices (identifier, certificate, name, type) VALUES (?, ?, ?, ?)"
    self._execute(query, (identifier, certificate, name, device))

  def unpairDevice(self, identifier):
    query = "DELETE FROM trusted_devices WHERE identifier = ?"
    self._execute(query, (identifier,))

  def persistNotification(self, identifier, text, title, application, reference):
    query = "INSERT INTO notifications (identifier, [text], title, application, reference) " \
      "VALUES (?, ?, ?, ?, ?) ON CONFLICT(identifier, reference) DO UPDATE SET text = excluded.text, " \
      "title = excluded.title, application = excluded.application"
    self._execute(query, (identifier, text, title, application, reference))

  def dismissNotification(self, identifier, reference):
    query = "DELETE FROM notifications WHERE identifier = ? AND reference = ?"
    self._execute(query, (identifier, reference))

  def cancelNotification(self, identifier, reference):
    query = "UPDATE notifications SET cancel = ? WHERE identifier = ? AND reference = ?"
    self._execute(query, (1, identifier, reference))

  def listNotifications(self, identifier):
    query = "SELECT cancel, reference, [text], title, application FROM notifications WHERE identifier = ?"
    return self._execute(query, (identifier,))

  def listAllNotifications(self):
    query = "SELECT d.identifier, d.name AS device, n.reference, n.[text], n.title, n.application, n.cancel " \
      "FROM notifications n INNER JOIN trusted_devices d ON (n.identifier = d.identifier) ORDER BY 2, 4"
    return self._execute(query)

  def addCommand(self, identifier, key, name, command):
    query = "INSERT INTO commands (key, identifier, name, command) VALUES (?, ?, ?, ?)"
    self._execute(query, (key, identifier, name, command))

  def updateCommand(self, identifier, key, name, command):
    query = "UPDATE commands SET name = ?, command = ? WHERE identifier = ? AND key = ?"
    self._execute(query, (name, command, identifier, key))

  def remCommands(self, identifier):
    query = "DELETE FROM commands WHERE identifier = ?"
    self._execute(query, (identifier,))

  def remCommand(self, identifier, key):
    query = "DELETE FROM commands WHERE identifier = ? AND key = ?"
    self._execute(query, (identifier, key))

  def getCommand(self, identifier, key):
    query = "SELECT command FROM commands WHERE identifier = ? AND key = ?"
    try:
      return self._execute(query, (identifier, key))[0]["command"]
    except IndexError:
      return None

  def listCommands(self, identifier):
    query = "SELECT key, name, command FROM commands WHERE identifier = ?"
    return self._execute(query, (identifier,))

  def listAllCommands(self):
    query = "SELECT d.identifier, d.name AS device, c.key, c.name, c.command FROM commands c " \
      "INNER JOIN trusted_devices d ON (c.identifier = d.identifier) ORDER BY 2, 4"
    return self._execute(query)

  def getPath(self, identifier):
    query = "SELECT path FROM trusted_devices WHERE identifier = ?"
    try:
      return self._execute(query, (identifier, ))[0]["path"]
    except IndexError:
      return None

  def setPath(self, identifier, path=None):
    query = "UPDATE trusted_devices SET path = ? WHERE identifier = ?"
    self._execute(query, (path, identifier))
