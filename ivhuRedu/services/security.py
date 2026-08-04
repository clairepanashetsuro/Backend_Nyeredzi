

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# =======================================================================
# 2 & 3. JWT ACCESS TOKENS - creating (signing) and reading (verifying)
# =======================================================================
# Read from the environment rather than hardcoding - "Keep Secrets in a
# Vault, Not a File". SECRET_KEY has no safe default: if it's missing we
# want the app to refuse to start rather than silently sign tokens with a
# key anyone could read straight out of this file on GitHub.
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set. Generate one with "
        "`openssl rand -hex 32` and set it before starting the app."
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    THE TOKEN CREATOR
    Copies `data` (e.g. {"sub": user.phone_number}), stamps an expiry
    timestamp onto it, and signs the whole thing with SECRET_KEY. The
    result is a compact string that proves two things at once: who the
    holder claims to be, and that this server issued it (because only
    this server knows SECRET_KEY) - all without needing to store a
    session anywhere. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES if no
    custom expiry is given.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(
    data: dict,
    expires_delta=None,
):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expires_delta

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[dict]:
    """
    THE TOKEN READER
    Verifies the signature (proving it was issued by this server and
    hasn't been altered) and the expiry (proving it hasn't gone stale),
    then returns the payload - e.g. {"sub": "+263771234567", "exp": ...}.

    Returns None on ANY failure: bad signature, expired token, malformed
    token. The caller (dependencies.get_current_user) turns every one of
    those into the exact same generic 401 response - one signing
    algorithm, expiry always checked, and no hint to the caller about
    *which* part of the token was wrong.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None