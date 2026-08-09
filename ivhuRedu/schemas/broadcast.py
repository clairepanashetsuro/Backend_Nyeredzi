from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional

class BroadcastCreate(BaseModel):
    ward: str = Field(..., example="Ward 1")
    message: str = Field(..., example="Hello farmers! Meeting tomorrow at 10AM.")
    sent_by: UUID
    sent_by_name: str = Field(..., example="Extension Worker Rudo")
    recipient_type: str = Field(..., example="farmers")
    farmer_count: int = Field(0, ge=0, example=15)
    worker_count: int = Field(0, ge=0, example=0)
    phone_numbers: List[str] = Field(..., example=["+263772123456"])

class BroadcastResponse(BaseModel):
    broadcast_id: str
    status: str
    message: str
    ward: str
    recipient_type: str
    total_recipients: int
    sent_by: str
    sent_by_name: str
    created_at: str

class BroadcastSummaryResponse(BaseModel):
    total_broadcasts: int
    total_farmers: int
    total_workers: int
    recent: List[dict]
