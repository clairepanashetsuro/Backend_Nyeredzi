"""
dependencies.py
------------------
The security checkpoint and resource manager. Every route that needs a
database session or needs to know who is calling it depends on something
from this file, rather than re-implementing that logic itself.

1. Database Session Giver  -> get_db()
2. Token Decoder & Verification -> handled by services.security.decode_access_token,
   wired in below via get_current_user()
3. Current User Extractor -> get_current_user()
4. Role Checkers -> require_roles(), ensure_self_or_privileged()
"""

import uuid
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ivhuRedu.database import SessionLocal
from ivhuRedu.models.user import User, UserType
from ivhuRedu.repositories.user import user_repository
from ivhuRedu.services.security import decode_access_token

# Tells FastAPI/Swagger where the "Authorize" button should send
# credentials to obtain a token - the login route in routers/auth.py.
# This also makes oauth2_scheme automatically pull the bearer token out
# of the "Authorization: Bearer <token>" header on every request that
# depends on it, and return 401 by itself if that header is missing.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# =======================================================================
# 1. DATABASE SESSION GIVER
# =======================================================================
def get_db():
    """
    Grabs a temporary session from the session factory, hands it to
    whichever route depends on it, and closes that connection the moment
    the request finishes - success or failure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =======================================================================
# 2 & 3. TOKEN DECODER + CURRENT USER EXTRACTOR
# =======================================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Runs on every protected route:
      1. oauth2_scheme has already pulled the raw token string out of the
         Authorization header (or already returned 401 if it was missing).
      2. Decode + verify that token (signature valid, not expired).
      3. Pull the identity (phone_number) out of the token's "sub" claim.
      4. Look that user up in the database and confirm they still exist.

    Every failure path below raises the exact same generic 401 - a bad
    signature, an expired token, and "that user no longer exists" all
    look identical to the caller. Errors stay generic; specifics matter
    only in server logs, and only if you add logging here later.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    phone_number = payload.get("sub")
    if not phone_number:
        raise credentials_error

    user = user_repository.get_by_phone_number(db, phone_number)
    if user is None:
        raise credentials_error

    return user


# =======================================================================
# 4. ROLE CHECKERS
# =======================================================================
def require_roles(*allowed_roles: UserType):
    """
    Dependency FACTORY. Call it with the roles allowed through, and use
    the result as a dependency:

        @router.get("/", dependencies=[Depends(require_roles(UserType.ADMIN))])
        def list_everyone(...): ...

    Raises 403 Forbidden (not 404, and not a silent empty response) if
    the caller is authenticated but simply isn't allowed to do this -
    "if it answers 200 OK instead of 403 Forbidden, it is broken."
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.user_type not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker


def ensure_self_or_privileged(
    target_user_id: uuid.UUID,
    current_user: User,
    privileged_roles: Iterable[UserType] = (UserType.ADMIN, UserType.SUPERVISOR),
) -> None:
  
    if current_user.id != target_user_id and current_user.user_type not in privileged_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this user's data",
        )