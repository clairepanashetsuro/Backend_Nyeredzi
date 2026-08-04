from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ivhuRedu.dependencies import get_db
from ivhuRedu.models.otp import OTP, OTPPurpose
from ivhuRedu.models.user import User
from ivhuRedu.schemas.auth import Token
from ivhuRedu.schemas.otp import (
    ForgotPassword,
    ResetPassword,
    VerifyOTP,
)
from ivhuRedu.services import auth as auth_service
from ivhuRedu.services.otp import create_otp
from ivhuRedu.services.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


# ==========================================================
# Login
# ==========================================================

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    token_data = auth_service.login(
        db,
        phone_number=form_data.username,
        password=form_data.password,
    )

    return Token(**token_data)


# ==========================================================
# Forgot password
# ==========================================================

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPassword,
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(User.phone_number == data.phone_number)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    create_otp(
        db=db,
        user=user,
        purpose=OTPPurpose.PASSWORD_RESET,
    )

    return {
        "message": "Verification code sent."
    }


# ==========================================================
# Verify OTP
# ==========================================================

@router.post("/verify-otp")
def verify_otp(
    data: VerifyOTP,
    db: Session = Depends(get_db),
):

    otp = (
        db.query(OTP)
        .filter(OTP.code == data.code)
        .first()
    )

    if not otp:
        raise HTTPException(
            status_code=404,
            detail="Invalid verification code.",
        )

    if otp.used:
        raise HTTPException(
            status_code=400,
            detail="Code already used.",
        )

    if datetime.now(timezone.utc) > otp.expires_at:
        raise HTTPException(
            status_code=400,
            detail="Verification code expired.",
        )

    otp.attempts += 1

    if otp.attempts >= 5:
        raise HTTPException(
            status_code=403,
            detail="Too many attempts.",
        )

    otp.used = True

    db.commit()

    return {
        "message": "OTP verified successfully."
    }


# ==========================================================
# Reset password
# ==========================================================

@router.post("/reset-password")
def reset_password(
    data: ResetPassword,
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(User.phone_number == data.phone_number)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    user.hashed_password = hash_password(
        data.new_password
    )

    user.must_change_password = False

    db.commit()

    return {
        "message": "Password updated successfully."
    }