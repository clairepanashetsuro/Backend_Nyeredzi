import asyncio
import os
import secrets

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


async def hash_password(
    plain_password: str,
) -> str:
    """Hash a password asynchronously."""

    return await asyncio.to_thread(
        pwd_context.hash,
        plain_password,
    )


async def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password asynchronously."""

    return await asyncio.to_thread(
        pwd_context.verify,
        plain_password,
        hashed_password,
    )


async def hash_ussd_pin(
    pin: str,
) -> str:
    """Hash a USSD PIN asynchronously."""

    return await asyncio.to_thread(
        pwd_context.hash,
        pin,
    )


async def verify_ussd_pin(
    pin: str,
    hashed_pin: str,
) -> bool:
    """Verify a USSD PIN asynchronously."""

    return await asyncio.to_thread(
        pwd_context.verify,
        pin,
        hashed_pin,
    )


def generate_password_reset_otp() -> str:
    """
    Generate a cryptographically secure
    6-digit password reset OTP.
    """

    return f"{secrets.randbelow(1_000_000):06d}"


async def hash_password_reset_otp(
    otp: str,
) -> str:
    """Hash a password reset OTP asynchronously."""

    return await asyncio.to_thread(
        pwd_context.hash,
        otp,
    )


async def verify_password_reset_otp(
    otp: str,
    hashed_otp: str,
) -> bool:
    """Verify a password reset OTP asynchronously."""

    return await asyncio.to_thread(
        pwd_context.verify,
        otp,
        hashed_otp,
    )




ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "RS256",
)


PRIVATE_KEY_PATH = os.getenv(
    "JWT_PRIVATE_KEY_PATH",
    "keys/jwt_private.pem",
)


PUBLIC_KEY_PATH = os.getenv(
    "JWT_PUBLIC_KEY_PATH",
    "keys/jwt_public.pem",
)


ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60",
    )
)


REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "1",
    )
)


OFFLINE_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "OFFLINE_TOKEN_EXPIRE_DAYS",
        "14",
    )
)


PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
        "5",
    )
)


try:

    with open(
        PRIVATE_KEY_PATH,
        "r",
        encoding="utf-8",
    ) as private_key_file:
        PRIVATE_KEY = private_key_file.read()


    with open(
        PUBLIC_KEY_PATH,
        "r",
        encoding="utf-8",
    ) as public_key_file:
        PUBLIC_KEY = public_key_file.read()


except FileNotFoundError as exc:

    raise RuntimeError(
        "JWT RSA key files could not be found. "
        "Check JWT_PRIVATE_KEY_PATH and JWT_PUBLIC_KEY_PATH."
    ) from exc




async def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + (
            expires_delta
            or timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "token_type": "access",
        }
    )

    return await asyncio.to_thread(
        jwt.encode,
        to_encode,
        PRIVATE_KEY,
        algorithm=ALGORITHM,
    )




async def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + (
            expires_delta
            or timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "token_type": "refresh",
        }
    )

    return await asyncio.to_thread(
        jwt.encode,
        to_encode,
        PRIVATE_KEY,
        algorithm=ALGORITHM,
    )




async def create_offline_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + (
            expires_delta
            or timedelta(
                days=OFFLINE_TOKEN_EXPIRE_DAYS
            )
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "token_type": "offline",
        }
    )

    return await asyncio.to_thread(
        jwt.encode,
        to_encode,
        PRIVATE_KEY,
        algorithm=ALGORITHM,
    )




async def create_password_reset_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a short-lived token that can only be used
    to complete a password reset.

    This token is NOT an access token.
    """

    expire = (
        datetime.now(timezone.utc)
        + (
            expires_delta
            or timedelta(
                minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
            )
        )
    )

    payload = {
        "sub": user_id,
        "exp": expire,
        "token_type": "password_reset",
    }

    return await asyncio.to_thread(
        jwt.encode,
        payload,
        PRIVATE_KEY,
        algorithm=ALGORITHM,
    )




async def decode_token(
    token: str,
) -> Optional[dict]:

    try:

        return await asyncio.to_thread(
            jwt.decode,
            token,
            PUBLIC_KEY,
            algorithms=["RS256"],
        )

    except InvalidTokenError:

        return None