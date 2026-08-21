import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.repositories.password_reset_otp import (
    password_reset_otp_repository,
)
from ivhuRedu.repositories.user import (
    user_repository,
)
from ivhuRedu.services.security import (
    generate_password_reset_otp,
    hash_password_reset_otp,
    verify_password_reset_otp,
)

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_LOCK_MINUTES = 15
OTP_SEND_COOLDOWN_SECONDS = 60
OTP_MAX_SENDS_PER_HOUR = 3

async def request_password_reset(
    db: AsyncSession,
    phone_number: str,
) -> tuple[str | None, str | None]:

    user = await user_repository.get_by_phone_number(
        db,
        phone_number,
    )

    if user is None:
        return None, None

    now = datetime.now(timezone.utc)

    if user.is_locked:
        if (
            user.locked_until is None
            or user.locked_until > now
        ):
            return None, None

    latest_otp = (
        await password_reset_otp_repository
        .get_latest_by_user_id(
            db,
            user.id,
        )
    )

    if latest_otp and latest_otp.locked_until:
        if latest_otp.locked_until > now:
            return None, None

    if latest_otp:
        seconds_since_last_otp = (
            now - latest_otp.created_at
        ).total_seconds()

        if (
            seconds_since_last_otp
            < OTP_SEND_COOLDOWN_SECONDS
        ):
            return None, None

    recent_otp_count = (
        await password_reset_otp_repository
        .count_recent_by_user_id(
            db,
            user.id,
            minutes=60,
        )
    )

    if recent_otp_count >= OTP_MAX_SENDS_PER_HOUR:
        return None, None

    otp = generate_password_reset_otp()

    code_hash = await hash_password_reset_otp(
        otp,
    )

    expires_at = (
        now
        + timedelta(
            minutes=OTP_EXPIRY_MINUTES,
        )
    )

    await password_reset_otp_repository.create(
        db,
        {
            "user_id": user.id,
            "code_hash": code_hash,
            "attempts": 0,
            "expires_at": expires_at,
            "locked_until": None,
        },
    )

    return otp, user.phone_number

async def verify_password_reset_otp_code(
    db: AsyncSession,
    phone_number: str,
    otp_code: str,
) -> uuid.UUID:

    user = await user_repository.get_by_phone_number(
        db,
        phone_number,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset code."
            ),
        )

    now = datetime.now(timezone.utc)

    if user.is_locked:
        if (
            user.locked_until is None
            or user.locked_until > now
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked.",
            )

    otp_record = (
        await password_reset_otp_repository
        .get_latest_by_user_id(
            db,
            user.id,
        )
    )

    if otp_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset code."
            ),
        )

    if (
        otp_record.locked_until
        and otp_record.locked_until > now
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many failed attempts. "
                "Try again in 15 minutes."
            ),
        )

    if otp_record.expires_at <= now:
        await password_reset_otp_repository.delete(
            db,
            otp_record,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset code."
            ),
        )

    is_valid = await verify_password_reset_otp(
        otp_code,
        otp_record.code_hash,
    )

    if not is_valid:
        new_attempts = (
            otp_record.attempts + 1
        )

        if new_attempts >= OTP_MAX_ATTEMPTS:
            locked_until = (
                now
                + timedelta(
                    minutes=OTP_LOCK_MINUTES,
                )
            )
            await password_reset_otp_repository.update(
                db,
                otp_record,
                {
                    "attempts": new_attempts,
                    "locked_until": locked_until,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many failed attempts. "
                    "Try again in 15 minutes."
                ),
            )

        await password_reset_otp_repository.update(
            db,
            otp_record,
            {
                "attempts": new_attempts,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset code.",
        )

    user_id = user.id
    await password_reset_otp_repository.delete(
        db,
        otp_record,
    )
    return user_id
