from typing import Optional
import uuid

from pydantic import BaseModel


class FarmerRequestBase(BaseModel):
    phone_number: str
    request_type: str
    status: Optional[str] = "PENDING"
    ussd_session_id: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    farmer_id: Optional[uuid.UUID] = None
    assigned_worker_id: Optional[uuid.UUID] = None
    sync_status: Optional[str] = None
    resolved_at: Optional[str] = None


class FarmerRequestCreate(FarmerRequestBase):
    pass


class FarmerRequestUpdate(BaseModel):
    phone_number: Optional[str] = None
    request_type: Optional[str] = None
    status: Optional[str] = None
    ussd_session_id: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    farmer_id: Optional[uuid.UUID] = None
    assigned_worker_id: Optional[uuid.UUID] = None
    sync_status: Optional[str] = None
    resolved_at: Optional[str] = None