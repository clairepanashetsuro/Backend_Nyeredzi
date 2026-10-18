import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from ivhuRedu.services import security
from tests.conftest import OTHER_PRIVATE_PEM, TEST_PRIVATE_PEM, TEST_PUBLIC_PEM


async def test_hash_password_returns_bcrypt_hash_not_plaintext():
    hashed = await security.hash_password("Password123")
    assert hashed != "Password123"
    assert hashed.startswith("$2")


async def test_verify_password_correct_password_returns_true():
    hashed = await security.hash_password("Password123")
    assert await security.verify_password("Password123", hashed) is True


@pytest.mark.parametrize(
    "wrong", ["password123", "Password124", "", " Password123", "Password123 "]
)
async def test_verify_password_wrong_password_returns_false(wrong):
    hashed = await security.hash_password("Password123")
    assert await security.verify_password(wrong, hashed) is False


async def test_hash_password_same_input_gives_different_hashes_due_to_salt():
    a = await security.hash_password("Password123")
    b = await security.hash_password("Password123")
    assert a != b
    assert await security.verify_password("Password123", a)
    assert await security.verify_password("Password123", b)


async def test_hash_password_supports_unicode():
    hashed = await security.hash_password("pässwörd-密码-🔐")
    assert await security.verify_password("pässwörd-密码-🔐", hashed)


async def test_verify_password_with_garbage_hash_raises():
    with pytest.raises(Exception):
        await security.verify_password("Password123", "not-a-hash")


@pytest.mark.parametrize(
    "hash_fn, verify_fn",
    [
        (security.hash_ussd_pin, security.verify_ussd_pin),
        (security.hash_password_reset_otp, security.verify_password_reset_otp),
    ],
)
async def test_pin_and_otp_hash_roundtrip(hash_fn, verify_fn):
    hashed = await hash_fn("123456")
    assert await verify_fn("123456", hashed) is True
    assert await verify_fn("654321", hashed) is False


@pytest.mark.parametrize(
    "raw, expected",
    [(0, "000000"), (42, "000042"), (999_999, "999999"), (123_456, "123456")],
)
def test_generate_password_reset_otp_zero_pads_to_six_digits(
    monkeypatch, raw, expected
):
    monkeypatch.setattr(security.secrets, "randbelow", lambda _n: raw)
    assert security.generate_password_reset_otp() == expected


def test_generate_password_reset_otp_real_values_are_six_digit_strings():
    for _ in range(200):
        otp = security.generate_password_reset_otp()
        assert len(otp) == 6 and otp.isdigit()


def test_generate_password_reset_otp_uses_full_million_range(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        security.secrets, "randbelow", lambda n: seen.setdefault("n", n) and 1
    )
    security.generate_password_reset_otp()
    assert seen["n"] == 1_000_000


@pytest.mark.parametrize(
    "factory, expected_type",
    [
        (security.create_access_token, "access"),
        (security.create_refresh_token, "refresh"),
        (security.create_offline_token, "offline"),
    ],
)
async def test_token_factories_embed_type_and_claims(factory, expected_type):
    token = await factory({"sub": "abc", "role": "admin"})
    payload = await security.decode_token(token)
    assert payload["token_type"] == expected_type
    assert payload["sub"] == "abc"
    assert payload["role"] == "admin"
    assert "exp" in payload


async def test_create_access_token_does_not_mutate_input_dict():
    data = {"sub": "abc"}
    await security.create_access_token(data)
    assert data == {"sub": "abc"}


@pytest.mark.parametrize(
    "factory, default_delta",
    [
        (
            security.create_access_token,
            timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES),
        ),
        (
            security.create_refresh_token,
            timedelta(days=security.REFRESH_TOKEN_EXPIRE_DAYS),
        ),
        (
            security.create_offline_token,
            timedelta(days=security.OFFLINE_TOKEN_EXPIRE_DAYS),
        ),
    ],
)
async def test_token_default_expiry(factory, default_delta):
    payload = await security.decode_token(await factory({"sub": "x"}))
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    expected = datetime.now(timezone.utc) + default_delta
    assert abs((exp - expected).total_seconds()) < 10


async def test_custom_expiry_overrides_default():
    token = await security.create_access_token(
        {"sub": "x"}, expires_delta=timedelta(seconds=30)
    )
    payload = await security.decode_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert (exp - datetime.now(timezone.utc)).total_seconds() < 35


async def test_expired_token_decodes_to_none():
    token = await security.create_access_token(
        {"sub": "x"}, expires_delta=timedelta(seconds=-5)
    )
    assert await security.decode_token(token) is None


async def test_password_reset_token_has_subject_type_and_short_expiry():
    token = await security.create_password_reset_token("user-1")
    payload = await security.decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["token_type"] == "password_reset"
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert (
        exp - datetime.now(timezone.utc)
    ).total_seconds() <= security.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60 + 5


async def test_decode_token_rejects_token_signed_with_other_key():
    forged = jwt.encode(
        {"sub": "x", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        OTHER_PRIVATE_PEM,
        algorithm="RS256",
    )
    assert await security.decode_token(forged) is None


async def test_decode_token_rejects_tampered_payload():
    token = await security.create_access_token({"sub": "x", "role": "farmer"})
    header, payload, signature = token.split(".")
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    data["role"] = "admin"
    forged_payload = (
        base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()
    )
    assert await security.decode_token(f"{header}.{forged_payload}.{signature}") is None


async def test_decode_token_rejects_alg_none_token():
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': 'x', 'token_type': 'access'})}."
    assert await security.decode_token(token) is None


@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c", "....", "Bearer xyz"])
async def test_decode_token_garbage_returns_none(garbage):
    assert await security.decode_token(garbage) is None


def test_decode_key_content_passes_pem_through():
    assert (
        security._decode_key_content("  " + TEST_PUBLIC_PEM + "\n")
        == TEST_PUBLIC_PEM.strip()
    )


def test_decode_key_content_decodes_base64_pem():
    encoded = base64.b64encode(TEST_PUBLIC_PEM.encode()).decode()
    assert security._decode_key_content(encoded) == TEST_PUBLIC_PEM


def test_decode_key_content_invalid_base64_returns_original():
    assert security._decode_key_content("%%%not base64%%%") == "%%%not base64%%%"


def test_get_private_key_reads_from_file_when_env_missing(monkeypatch, tmp_path):
    key_file = tmp_path / "priv.pem"
    key_file.write_text(TEST_PRIVATE_PEM)
    monkeypatch.setattr(security, "_PRIVATE_KEY", None)
    monkeypatch.delenv("JWT_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(key_file))
    assert security._get_private_key() == TEST_PRIVATE_PEM


def test_get_public_key_missing_file_raises_runtime_error(monkeypatch, tmp_path):
    monkeypatch.setattr(security, "_PUBLIC_KEY", None)
    monkeypatch.delenv("JWT_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(tmp_path / "missing.pem"))
    with pytest.raises(RuntimeError, match="JWT public key not found"):
        security._get_public_key()


def test_get_private_key_missing_file_raises_runtime_error(monkeypatch, tmp_path):
    monkeypatch.setattr(security, "_PRIVATE_KEY", None)
    monkeypatch.delenv("JWT_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(tmp_path / "missing.pem"))
    with pytest.raises(RuntimeError, match="JWT private key not found"):
        security._get_private_key()


def test_keys_are_cached_after_first_load(monkeypatch):
    monkeypatch.setattr(security, "_PRIVATE_KEY", "cached-value")
    assert security._get_private_key() == "cached-value"
