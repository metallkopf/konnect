#!/usr/bin/env python3

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.x509 import Name, NameAttribute, CertificateBuilder
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.hashes import SHA256
from datetime import datetime, timedelta
from os.path import exists
from logging import debug, info, warning, error


CERT_FILE = "certificate.pem"
KEY_FILE = "privateKey.pem"


def generate_selfsigned(identifier):
  if exists(CERT_FILE) and exists(KEY_FILE):
    return

  debug("Generating private key")
  key = generate_private_key(65537, 2048, default_backend())

  with open(KEY_FILE, "wb") as pem:
    pem.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))

  subject = issuer = Name([
    NameAttribute(NameOID.COMMON_NAME, identifier),
    NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "KDE Connect"),
    NameAttribute(NameOID.ORGANIZATION_NAME, "KDE"),
  ])

  before = datetime.utcnow() - timedelta(days=365)
  after = before + timedelta(days=3650)
  debug("Generating certificate")
  cert = CertificateBuilder().subject_name(subject).issuer_name(issuer).\
    public_key(key.public_key()).serial_number(1).not_valid_before(before).\
    not_valid_after(after).sign(key, SHA256(), default_backend())

  with open(CERT_FILE, "wb") as pem:
    pem.write(cert.public_bytes(Encoding.PEM))
