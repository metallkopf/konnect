#!/usr/bin/env python3

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.x509 import Name, NameAttribute, CertificateBuilder, SubjectAlternativeName, DNSName
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.hashes import SHA256
from datetime import datetime, timedelta

key = generate_private_key(65537, 2048, default_backend())

with open("privatekey.pem", "wb") as f:
    f.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))

identifier = "d41d8cd98f00b204e9800998ecf8427e"#"b7301ce0878a0ffc"#"_eef31d70_5060_44c1_a4ae_489a46b78790_"

subject = issuer = Name([
    NameAttribute(NameOID.COMMON_NAME, identifier),
    NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "KDE Connect"),
    NameAttribute(NameOID.ORGANIZATION_NAME, "KDE"),
])

before = datetime.utcnow() - timedelta(days=365)
after = before + timedelta(days=3650)

cert = CertificateBuilder().subject_name(subject).issuer_name(issuer).\
  public_key(key.public_key()).serial_number(1).not_valid_before(before).\
  not_valid_after(after).sign(key, SHA256(), default_backend())

with open("certificate.pem", "wb") as f:
    f.write(cert.public_bytes(Encoding.PEM))