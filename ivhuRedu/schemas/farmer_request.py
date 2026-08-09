import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum

class RequestType(str, Enum):
    visit_request = "visit_request"
    advice_request = "advice_request"
    land_degradation_report = "land_degradation_report"

class RequestStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    resolved = "resolved"
    cancelled = "cancelled"

class FarmerRequestBase(BaseModel):
    request_type: RequestType
    ussd_input_text: Optional[float] = None
    distance_m: Optional[float] = None
    sync_status: Optional[str] = "pending_sync"
    farmer_id: Optional[uuid.UUID] = None
    worker_id: Optional[uuid.UUID] = None

class FarmerRequestCreate(FarmerRequestBase):
    pass

class FarmerRequestUpdate(BaseModel):
    request_type: Optional[RequestType] = None
    ussd_input_text: Optional[float] = None
    distance_m: Optional[float] = None
    request_status: Optional[RequestStatus] = None
    sync_status: Optional[str] = None
    worker_id: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None

class FarmerRequestOut(FarmerRequestBase):
    request_id: uuid.UUID
    request_status: RequestStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
