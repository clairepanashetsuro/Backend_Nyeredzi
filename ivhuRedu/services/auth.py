from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.user import User, UserType
from ivhuRedu.repositories.user import user_repository
from ivhuRedu.services.security import (
    create_access_token,
    create_offline_token,
    create_refresh_token,
    hash_password,
    verify_password,
)


async def authenticate_user(
    db: AsyncSession,
    phone_number: str,
    password: str,
):
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect phone number or password",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    user = await user_repository.get_by_phone_number(
        db,
        phone_number,
    )

    if not user:
        raise invalid_credentials

    if not user.hashed_password:
        raise invalid_credentials

    if not await verify_password(
        password,
        user.hashed_password,
    ):
        raise invalid_credentials

    return user


async def login(
    db: AsyncSession,
    phone_number: str,
    password: str,
):
    user = await authenticate_user(
        db,
        phone_number,
        password,
    )

    if user.user_type == UserType.FARMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmers use the USSD system.",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked.",
        )

    if user.user_type == UserType.EXTENSION_WORKER:
        access_expiry = timedelta(hours=1)
        refresh_expiry = timedelta(days=1)

    elif user.user_type == UserType.SUPERVISOR:
        access_expiry = timedelta(hours=1)
        refresh_expiry = timedelta(days=1)

    elif user.user_type == UserType.ADMIN:
        access_expiry = timedelta(minutes=60)
        refresh_expiry = timedelta(days=1)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unsupported user type.",
        )

    token_data = {
        "sub": str(user.id),
        "role": user.user_type.value,
    }

    access_token = await create_access_token(
        data=token_data,
        expires_delta=access_expiry,
    )

    refresh_token = await create_refresh_token(
        data=token_data,
        expires_delta=refresh_expiry,
    )

    offline_token = None

    if user.user_type == UserType.EXTENSION_WORKER:
        offline_token = await create_offline_token(
            data=token_data,
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "offline_token": offline_token,
        "token_type": "bearer",
        "role": user.user_type.value,
        "must_change_password": user.must_change_password,
    }


async def change_password(
    db: AsyncSession,
    user: User,
    old_password: str,
    new_password: str,
):
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account does not have a password.",
        )

    if not await verify_password(
        old_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )

    if await verify_password(
        new_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the old password.",
        )

    user.hashed_password = await hash_password(
        new_password
    )

    user.must_change_password = False

    await db.commit()
    await db.refresh(user)

    return {
        "message": "Password changed successfully."
    }
