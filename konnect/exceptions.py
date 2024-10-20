class ApiError(Exception):
  def __init__(self, message, code=500, parent=None):
    super().__init__(message)
    self.code = code
    self.parent = str(parent) if parent else None


class UnknownError(ApiError):
  def __init__(self, parent=None):
    super().__init__("unknown error", 500, parent)


class UnserializationError(ApiError):
  def __init__(self, parent=None):
    super().__init__("unserialization error", 400, parent)


class InvalidRequestError(ApiError):
  def __init__(self, parent=None):
    super().__init__("invalid request", 400, parent)


class DeviceNotReachableError(ApiError):
  def __init__(self, parent=None):
    super().__init__("device not reachable", 404, parent)


class DeviceNotTrustedError(ApiError):
  def __init__(self, parent=None):
    super().__init__("device not paired", 401, parent)


class AlreadyPairedError(ApiError):
  def __init__(self, parent=None):
    super().__init__("already paired", 404, parent)


class NotImplementedError2(ApiError):
  def __init__(self, parent=None):
    super().__init__("not implemented", 501, parent)
