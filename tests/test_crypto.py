import pytest
from cryptography.fernet import Fernet, InvalidToken

from utils import crypto


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"hello",
        "unicode ✓ 密码".encode(),
        b"\x00\x01\x02" * 1000,
        b"x" * 1_000_000,
    ],
)
def test_encrypt_decrypt_roundtrip(data):
    assert crypto.decrypt_file_data(crypto.encrypt_file_data(data)) == data


def test_encrypted_bytes_differ_from_plaintext():
    assert b"secret-image-bytes" not in crypto.encrypt_file_data(b"secret-image-bytes")


def test_encryption_is_non_deterministic():
    assert crypto.encrypt_file_data(b"same") != crypto.encrypt_file_data(b"same")


def test_decrypt_tampered_data_raises_invalid_token():
    token = bytearray(crypto.encrypt_file_data(b"data"))
    token[-5] ^= 0x01
    with pytest.raises(InvalidToken):
        crypto.decrypt_file_data(bytes(token))


def test_decrypt_garbage_raises_invalid_token():
    with pytest.raises(InvalidToken):
        crypto.decrypt_file_data(b"definitely not fernet")


def test_decrypt_data_from_other_key_raises_invalid_token():
    foreign = Fernet(Fernet.generate_key()).encrypt(b"data")
    with pytest.raises(InvalidToken):
        crypto.decrypt_file_data(foreign)


def test_load_key_prefers_environment_variable(monkeypatch):
    monkeypatch.setenv("FILE_ENCRYPTION_KEY", "env-key-value")
    assert crypto._load_or_create_key() == b"env-key-value"


def test_load_key_reads_existing_file(monkeypatch, tmp_path):
    key_file = tmp_path / "keys" / "file_encryption.key"
    key_file.parent.mkdir()
    key_file.write_bytes(b"stored-key")
    monkeypatch.delenv("FILE_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(crypto, "_KEY_PATH", str(key_file))
    assert crypto._load_or_create_key() == b"stored-key"


def test_load_key_creates_valid_key_file_when_missing(monkeypatch, tmp_path):
    key_file = tmp_path / "newdir" / "file_encryption.key"
    monkeypatch.delenv("FILE_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(crypto, "_KEY_PATH", str(key_file))
    key = crypto._load_or_create_key()
    assert key_file.read_bytes() == key
    Fernet(key)
