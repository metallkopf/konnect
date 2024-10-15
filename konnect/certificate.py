from datetime import datetime, timedelta
from logging import debug
from os.path import join

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.x509 import CertificateBuilder, Name, NameAttribute
from cryptography.x509.oid import NameOID
from twisted.internet.ssl import PrivateCertificate


class Certificate:
  CERTIFICATE_FILE = "certificate.pem"
  PRIVATE_KEY_FILE = "privateKey.pem"

  @staticmethod
  def generate(identifier, path):
    debug("Generating private key")
    key = generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())

    with open(join(path, Certificate.PRIVATE_KEY_FILE), "wb+") as pem:
      pem.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))

    name = Name(
      [
        NameAttribute(NameOID.COMMON_NAME, identifier),
        NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "KDE Connect"),
        NameAttribute(NameOID.ORGANIZATION_NAME, "KDE"),
      ]
    )

    before = datetime.now() - timedelta(days=365)
    after = before + timedelta(days=3650)

    debug("Generating certificate")
    cert = CertificateBuilder().subject_name(name).issuer_name(name).\
      public_key(key.public_key()).serial_number(1).not_valid_before(before).\
      not_valid_after(after).sign(key, SHA256(), default_backend())

    with open(join(path, Certificate.CERTIFICATE_FILE), "wb+") as pem:
      pem.write(cert.public_bytes(Encoding.PEM))

  @staticmethod
  def extract_identifier(options):
    return options.certificate.get_subject().commonName

  @staticmethod
  def load_options(path):
    with open(join(path, Certificate.CERTIFICATE_FILE), "rb") as cert, \
      open(join(path, Certificate.PRIVATE_KEY_FILE), "rb") as key:
      certificate = cert.read() + key.read()

    pem = PrivateCertificate.loadPEM(certificate)

    return pem.options()
