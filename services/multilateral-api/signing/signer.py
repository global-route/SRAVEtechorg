import hashlib
import json
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption, load_pem_private_key
)


def sha256_sign(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def load_private_key() -> Ed25519PrivateKey | None:
    path = os.getenv("SIGNING_KEY_PATH")
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return load_pem_private_key(f.read(), password=None)


def get_public_key_pem() -> str:
    key = load_private_key()
    if not key:
        return ""
    return key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
