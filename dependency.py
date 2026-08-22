import uuid
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session

from ivhuRedu.models.user import User, UserType
from ivhuRedu.repositories.user import user_repository
from ivhuRedu.services.security import decode_token


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login"
)


async def get_db():
    async with async_session() as db:
        yield db


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )


    payload = await decode_token(token)

    if payload is None:
        raise credentials_error

    token_type = payload.get("token_type")

    if token_type not in (
        "access",
        "offline",
    ):
        raise credentials_error

    user_id = payload.get("sub")

    if not user_id:
        raise credentials_error

    try:
        user_uuid = uuid.UUID(user_id)

    except (ValueError, TypeError):
        raise credentials_error

    user = await user_repository.get(
        db,
        user_uuid,
    )

    if user is None:
        raise credentials_error

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked.",
        )

    if (
        token_type == "offline"
        and user.user_type != UserType.EXTENSION_WORKER
    ):
        raise credentials_error

    return user


def require_password_changed(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:

    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must change your password before continuing.",
        )

    return current_user


def require_roles(
    *allowed_roles: UserType,
):

    def role_checker(
        current_user: User = Depends(
            require_password_changed
        ),
    ) -> User:

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
    privileged_roles: Iterable[UserType] = (
        UserType.ADMIN,
        UserType.SUPERVISOR,
    ),
) -> None:

    if (
        current_user.id != target_user_id
        and current_user.user_type not in privileged_roles
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this user's data",
        )