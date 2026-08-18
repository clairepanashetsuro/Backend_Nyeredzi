import os
from cryptography.fernet import Fernet
_KEY_PATH = os.path.join(os.getcwd(), "keys", "file_encryption.key")


def _load_or_create_key() -> bytes:
    env_key = os.environ.get("FILE_ENCRYPTION_KEY")
    if env_key:
        return env_key.encode("utf-8")

    os.makedirs(os.path.dirname(_KEY_PATH), exist_ok=True)

    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            return f.read()

    key = Fernet.generate_key()
    with open(_KEY_PATH, "wb") as f:
        f.write(key)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt_file_data(data: bytes) -> bytes:
    """Encrypt raw file bytes before writing to disk."""
    return _fernet.encrypt(data)


def decrypt_file_data(token: bytes) -> bytes:
    """Decrypt bytes previously produced by encrypt_file_data."""
    return _fernet.decrypt(token)
