from pydantic import BaseModel


class ForgotPassword(BaseModel):
    phone_number: str


class VerifyOTP(BaseModel):
    phone_number: str
    code: str


class ResetPassword(BaseModel):
    phone_number: str
    code: str
    new_password: str