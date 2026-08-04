"""
services/auth.py
-------------------
Business logic for logging in: look the user up by phone number, check
their password against the stored hash, and hand back signed tokens if
everything succeeds.
"""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ivhuRedu.models.otp import OTPPurpose
from ivhuRedu.models.user import UserType
from ivhuRedu.repositories.user import user_repository
from ivhuRedu.services.otp import create_otp
from ivhuRedu.services.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)


def authenticate_user(
    db: Session,
    phone_number: str,
    password: str,
):
    """
    Validate the user's credentials.
    """

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect phone number or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = user_repository.get_by_phone_number(
        db,
        phone_number,
    )

    if not user:
        raise invalid_credentials

    if not user.hashed_password:
        raise invalid_credentials

    if not verify_password(
        password,
        user.hashed_password,
    ):
        raise invalid_credentials

    return user


def login(
    db: Session,
    phone_number: str,
    password: str,
):
    """
    Authenticate the user and return the appropriate tokens.
    """

    user = authenticate_user(
        db,
        phone_number,
        password,
    )

    # Farmers should never log in through the API.
    if user.user_type == UserType.FARMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmers use the USSD system.",
        )

    # Prevent locked users from logging in.
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked.",
        )

    # Force first-time users to reset their passwords.
    if user.must_change_password:

        create_otp(
            db=db,
            user=user,
            purpose=OTPPurpose.FIRST_LOGIN,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Password reset required. "
                "A verification code has been sent."
            ),
        )

    # Token durations
    if user.user_type == UserType.EXTENSION_WORKER:

        access_expiry = timedelta(hours=12)
        refresh_expiry = timedelta(days=30)

    elif user.user_type == UserType.SUPERVISOR:

        access_expiry = timedelta(hours=1)
        refresh_expiry = timedelta(days=14)

    else:

        access_expiry = timedelta(minutes=30)
        refresh_expiry = timedelta(days=7)

    access_token = create_access_token(
        data={
            "sub": user.phone_number,
        },
        expires_delta=access_expiry,
    )

    refresh_token = create_refresh_token(
        data={
            "sub": user.phone_number,
        },
        expires_delta=refresh_expiry,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
