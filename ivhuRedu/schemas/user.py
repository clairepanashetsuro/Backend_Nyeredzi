import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
)

from ivhuRedu.models.user import UserType


PHONE_REGEX = re.compile(
    r"^\+?[0-9]{7,15}$"
)




class UserBase(BaseModel):

    first_name: str
    last_name: str
    phone_number: str

    email: Optional[EmailStr] = None

    

    @field_validator("phone_number")
    @classmethod
    def phone_number_must_look_valid(
        cls,
        value: str,
    ) -> str:

        if not PHONE_REGEX.match(value):
            raise ValueError(
                "phone_number must contain only digits "
                "(7-15 of them), with an optional leading +"
            )

        return value

    

    @field_validator("first_name", "last_name")
    @classmethod
    def names_must_not_be_blank(
        cls,
        value: str,
    ) -> str:

        if not value.strip():
            raise ValueError(
                "must not be blank"
            )

        return value




class UserCreate(UserBase):

    password: Optional[str] = None


    @field_validator("password")
    @classmethod
    def password_must_be_long_enough(
        cls,
        value: Optional[str],
    ) -> Optional[str]:

        if value is not None and len(value) < 8:
            raise ValueError(
                "password must be at least 8 characters long"
            )

        return value



class UserUpdate(BaseModel):

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None

    

    @field_validator("phone_number")
    @classmethod
    def phone_number_must_look_valid(
        cls,
        value: Optional[str],
    ) -> Optional[str]:

        if (
            value is not None
            and not PHONE_REGEX.match(value)
        ):
            raise ValueError(
                "phone_number must contain only digits "
                "(7-15 of them), with an optional leading +"
            )

        return value


    @field_validator("password")
    @classmethod
    def password_must_be_long_enough(
        cls,
        value: Optional[str],
    ) -> Optional[str]:

        if value is not None and len(value) < 8:
            raise ValueError(
                "password must be at least 8 characters long"
            )

        return value




class UserRead(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: uuid.UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone_number: str
    user_type: UserType
    created_at: datetime
    updated_at: datetime
