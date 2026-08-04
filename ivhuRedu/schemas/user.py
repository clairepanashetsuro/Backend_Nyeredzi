"""
schemas/user.py
------------------
Pydantic schemas for the User entity - the exact shape of the JSON coming
in on a request and going out on a response. These are kept separate from
the SQLAlchemy model on purpose:

  * They validate incoming data (type, format, range) before it ever
    touches the database.
  * UserCreate/UserUpdate only ever list the fields a client is allowed
    to set, so a request body can never smuggle in an unexpected field
    like "id" or "hashed_password" directly (mass-assignment protection:
    accept only the fields you have listed).
  * hashed_password never appears in ANY schema below - not even
    UserRead. A password hash should never be sent back to a client.

The most important piece of business logic lives on UserCreate: email and
password are required for everyone except a farmer. That rule has to live
here (not on the database column) because a column constraint is either
"always required" or "always optional" - it can't say "required, except
when user_type == farmer".
"""

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from ivhuRedu.models.user import UserType

# Permissive check for phone numbers such as "+263771234567" or
# "0771234567" - digits only, optional leading "+", 7-15 digits long.
PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")


class UserBase(BaseModel):
    """Fields shared by every shape of "a user" below."""

    first_name: str
    last_name: str
    phone_number: str
    user_type: UserType

    # Optional at this shared level; UserCreate decides whether it is
    # actually required, based on user_type.
    email: Optional[EmailStr] = None

    @field_validator("phone_number")
    @classmethod
    def phone_number_must_look_valid(cls, value: str) -> str:
        """Reject an obviously malformed phone number before it is saved."""
        if not PHONE_REGEX.match(value):
            raise ValueError(
                "phone_number must contain only digits (7-15 of them), with an optional leading +"
            )
        return value

    @field_validator("first_name", "last_name")
    @classmethod
    def names_must_not_be_blank(cls, value: str) -> str:
        """Reject empty or whitespace-only names."""
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class UserCreate(UserBase):
    """Every field a client may send when creating a user."""

    # Plain-text password as typed by the user. It is hashed in the
    # service layer (services/user.py) before anything is saved - the
    # database column is called hashed_password and never sees this raw
    # value.
    password: Optional[str] = None

    @model_validator(mode="after")
    def enforce_credentials_by_role(self) -> "UserCreate":
        """
        Business rule: every role except FARMER must supply both an email
        and a password, because extension workers, district supervisors
        and admins all log in to the web dashboard. Farmers are
        identified purely by phone number via USSD/SMS, so both stay
        optional for them.
        """
        if self.user_type != UserType.FARMER:
            if not self.email:
                raise ValueError("email is required for this user_type")
            if not self.password or len(self.password) < 8:
                raise ValueError(
                    "password is required for this user_type and must be at least 8 characters long"
                )
        return self


class UserUpdate(BaseModel):
    """
    Every field is optional here, and the service layer only applies the
    fields that were actually sent (exclude_unset=True) - a PUT with just
    {"last_name": "Moyo"} will not wipe out the user's other fields.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    user_type: Optional[UserType] = None

    @field_validator("phone_number")
    @classmethod
    def phone_number_must_look_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not PHONE_REGEX.match(value):
            raise ValueError(
                "phone_number must contain only digits (7-15 of them), with an optional leading +"
            )
        return value

    @field_validator("password")
    @classmethod
    def password_must_be_long_enough(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) < 8:
            raise ValueError("password must be at least 8 characters long")
        return value


class UserRead(BaseModel):
    """
    Shape of a user as returned to a client. Deliberately does NOT include
    hashed_password - a password hash should never leave the server.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone_number: str
    user_type: UserType
    created_at: datetime
    updated_at: datetime