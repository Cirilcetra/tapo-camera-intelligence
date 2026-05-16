import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings


def _get_fernet() -> Fernet:
    """Derive a stable 32-byte Fernet key from SECRET_KEY."""
    raw = settings.SECRET_KEY.encode()
    key_bytes = hashlib.sha256(raw).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_password(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
