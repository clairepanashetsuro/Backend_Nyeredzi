
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
