"""
Self-signed HTTPS certificate, generated in pure Python (no Node.js, no
openssl CLI, no npx office-addin-dev-certs). This is what lets DocFlow ship
as a single standalone executable with zero external tooling required.

Office Add-ins require HTTPS even on localhost, so we need *some*
certificate. On first run this generates a self-signed cert for
"localhost" / 127.0.0.1, valid for 2 years, and saves it under the user's
own profile directory so it persists across runs (and across PyInstaller
rebuilds, since it's written to a per-user data dir, not next to the exe).

The certificate still has to be TRUSTED by the browser once -- that's what
trust_certificate.ps1 does. Generating it here just removes the need for
any extra tooling to create it in the first place.
"""
import datetime
import os
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def cert_dir():
    """Per-user, writable regardless of whether we're running from a
    PyInstaller-frozen exe (which may sit in a read-only Program Files
    folder) or from source."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "DocFlow", "certs")
    os.makedirs(d, exist_ok=True)
    return d


def cert_paths():
    d = cert_dir()
    return os.path.join(d, "localhost.crt"), os.path.join(d, "localhost.key")


def ensure_cert():
    """Return (cert_path, key_path), generating a fresh self-signed pair
    if one doesn't already exist."""
    cert_path, key_path = cert_paths()
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    print("No certificate found -- generating a new self-signed one for localhost...")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DocFlow (local, self-signed)"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=730))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    print(f"Certificate written to {cert_path}")
    print("Run trust_certificate.ps1 once (see README) so your browser trusts it.")
    return cert_path, key_path


if __name__ == "__main__":
    c, k = ensure_cert()
    print(c)
    print(k)
