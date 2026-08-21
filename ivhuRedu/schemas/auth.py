from typing import Optional

from pydantic import BaseModel, Field





class Token(BaseModel):

    access_token: str

    refresh_token: str

    offline_token: Optional[str] = None

    token_type: str

    role: str

    must_change_password: bool





class RefreshTokenRequest(BaseModel):

    refresh_token: str





class ChangePasswordRequest(BaseModel):

    old_password: str

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )





class ForgotPasswordRequest(BaseModel):

    phone_number: str = Field(
        min_length=7,
        max_length=20,
    )


class ForgotPasswordResponse(BaseModel):

    message: str





class VerifyPasswordResetOTPRequest(BaseModel):

    phone_number: str = Field(
        min_length=7,
        max_length=20,
    )

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


class VerifyPasswordResetOTPResponse(BaseModel):

    reset_token: str





class ResetPasswordRequest(BaseModel):

    reset_token: str

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )