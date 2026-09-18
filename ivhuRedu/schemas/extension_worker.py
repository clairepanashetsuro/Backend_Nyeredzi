import uuid
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from ivhuRedu.models.extension_worker import (
    WorkerAvailabilityStatus,
)


class ExtensionWorkerCreate(BaseModel):
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

    email: Optional[EmailStr] = None

    password: str = Field(
        ...,
        min_length=8,
    )

    ussd_pincode: str = Field(
        ...,
        min_length=4,
        max_length=4,
    )

    assigned_ward_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    location_id: uuid.UUID

    @field_validator("ussd_pincode")
    @classmethod
    def validate_ussd_pincode(
        cls,
        value: str,
    ) -> str:
        if not value.isdigit():
            raise ValueError(
                "USSD PIN must contain only numbers"
            )

        return value


class ExtensionWorkerUpdate(BaseModel):
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

    email: Optional[EmailStr] = None

    password: Optional[str] = Field(
        default=None,
        min_length=8,
    )

    assigned_ward_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    location_id: Optional[uuid.UUID] = None

    ussd_pincode: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=4,
    )

    @field_validator("ussd_pincode")
    @classmethod
    def validate_ussd_pincode(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return value

        if not value.isdigit():
            raise ValueError(
                "USSD PIN must contain only numbers"
            )

        return value


class ExtensionWorkerRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    worker_id: uuid.UUID
    user_id: uuid.UUID
    location_id: uuid.UUID
    assigned_ward_name: str
    availability_status: WorkerAvailabilityStatus
    created_at: datetime
    last_updated_at: datetime


class ExtensionWorkerStatusUpdate(BaseModel):
    availability_status: WorkerAvailabilityStatus