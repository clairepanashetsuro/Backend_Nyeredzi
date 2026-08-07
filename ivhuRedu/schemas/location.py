from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class LocationBase(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str = Field(max_length=250)
    display_name: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    address: Optional[str] = Field(default=None, max_length=250)
    display_name: Optional[str] = None

class LocationResponse(LocationBase):
    location_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LocationGeocodeRequest(BaseModel):
    address: str = Field(min_length=1)

class NearbyWorkerResponse(BaseModel):
    user_id: UUID
    name: str
    phone: str
    role: str
    latitude: float
    longitude: float
    distance_km: float

    