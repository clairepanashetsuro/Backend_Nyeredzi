import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = os.getenv("IMAGE_ENCRYPTION_KEY")
if not SECRET_KEY:
    SECRET_KEY = Fernet.generate_key().decode()

fernet = Fernet(SECRET_KEY.encode())

def encrypt_file_data(raw_bytes: bytes) -> bytes:
    """Transforms readable image data into secure encrypted binary gibberish."""
    return fernet.encrypt(raw_bytes)

def decrypt_file_data(encrypted_bytes: bytes) -> bytes:
    """Restores encrypted binary gibberish back into a viewable image file."""
    return fernet.decrypt(encrypted_bytes)
