import re
import uuid

from datetime import datetime
from typing import Optional
from ivhuRedu.schemas.user import UserDetailsRead

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


PHONE_REGEX = re.compile(
    r"^\+?[0-9]{7,15}$"
)


class LocationRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    location_id: uuid.UUID
    latitude: float
    longitude: float
    address: str
    display_name: Optional[str] = None


class FarmerCreate(BaseModel):

    first_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    last_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    phone_number: str = Field(
        ...,
        max_length=20,
    )

    primary_crop: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    ward_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    location_id: uuid.UUID

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


class FarmerRead(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    farmer_id: uuid.UUID
    user_id: uuid.UUID

    ward_name: str
    primary_crop: Optional[str] = None

    location_id: uuid.UUID
    location: LocationRead

    created_at: datetime
    updated_at: datetime

    user: UserDetailsRead




class FarmerUpdate(BaseModel):

    first_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    last_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
    )

    ward_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    primary_crop: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    location_id: Optional[uuid.UUID] = None

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