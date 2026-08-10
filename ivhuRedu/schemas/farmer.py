import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,

)

from typing import Optional
from pydantic import BaseModel, EmailStr
import uuid





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




class FarmerRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    farmer_id: uuid.UUID
    user_id: uuid.UUID
    ward_name: str
    primary_crop: Optional[str]
    location_id: uuid.UUID
    created_at: datetime
    updated_at: datetime




class FarmerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    ward_name: Optional[str] = None
    primary_crop: Optional[str] = None
    location_id: Optional[uuid.UUID] = None