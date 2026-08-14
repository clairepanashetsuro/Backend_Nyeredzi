from datetime import datetime, timedelta, timezone
from typing import Optional
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from ivhuRedu.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )

def hash_ussd_pin(pin: str) -> str:
    return pwd_context.hash(pin)

def verify_ussd_pin(
    pin: str,
    hashed_pin: str,
) -> bool:
    return pwd_context.verify(
        pin,
        hashed_pin,
    )

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
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

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set."
    )

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )
    to_encode.update(
        {
            "exp": expire,
            "token_type": "access",
        }
    )
    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    )
    to_encode.update(
        {
            "exp": expire,
            "token_type": "refresh",
        }
    )
    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

def create_offline_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(
            days=OFFLINE_TOKEN_EXPIRE_DAYS
        )
    )
    to_encode.update(
        {
            "exp": expire,
            "token_type": "offline",
        }
    )
    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

def decode_token(
    token: str,
) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except JWTError:
        return None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    result = await db.execute(select(User).where(User.email == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
