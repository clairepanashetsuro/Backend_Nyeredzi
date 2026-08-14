import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from ivhuRedu.services.security import get_current_user



from ivhuRedu.models.user import User, UserType

from ivhuRedu.schemas.auth import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    Token,
)

from ivhuRedu.services import auth as auth_service

from ivhuRedu.repositories.user import user_repository

from ivhuRedu.services.security import (
    create_access_token,
    create_offline_token,
    decode_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/login",
    response_model=Token,
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    token_data = await auth_service.login(
        db,
        phone_number=form_data.username,
        password=form_data.password,
    )

    return Token(**token_data)


@router.post(
    "/change-password",
)
async def change_user_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await auth_service.change_password(
        db=db,
        user=current_user,
        old_password=data.old_password,
        new_password=data.new_password,
    )


@router.post(
    "/refresh-token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):

    payload = decode_token(
        data.refresh_token
    )

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    try:
        user_uuid = uuid.UUID(
            user_id
        )

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    user = await user_repository.get(
        db,
        user_uuid,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked.",
        )

    token_data = {
        "sub": str(user.id),
        "role": user.user_type.value,
    }

    access_token = create_access_token(
        data=token_data,
    )

    offline_token = None

    if user.user_type == UserType.EXTENSION_WORKER:
        offline_token = create_offline_token(
            data=token_data,
        )

    return {
        "access_token": access_token,
        "offline_token": offline_token,
        "token_type": "bearer",
        "role": user.user_type.value,
        "must_change_password": user.must_change_password,
    }