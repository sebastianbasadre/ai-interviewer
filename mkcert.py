"""Generate a self-signed TLS cert for local dev. Run once after each wsl --shutdown."""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime, ipaddress, pathlib

k = rsa.generate_private_key(65537, 2048)
n = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "homelab")])
c = (
    x509.CertificateBuilder()
    .subject_name(n).issuer_name(n)
    .public_key(k.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    .add_extension(x509.SubjectAlternativeName([
        x509.IPAddress(ipaddress.IPv4Address("192.168.2.6")),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]), critical=False)
    .sign(k, hashes.SHA256())
)
p = pathlib.Path("/tmp/devcert")
p.mkdir(exist_ok=True)
(p / "key.pem").write_bytes(k.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
))
(p / "cert.pem").write_bytes(c.public_bytes(serialization.Encoding.PEM))
print("Cert written to /tmp/devcert/")
