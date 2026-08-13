from pydantic import BaseModel
from uuid import UUID
from typing import List


class BroadcastCreate(BaseModel):
    ward: str
    message: str
    sent_by: UUID
    sent_by_name: str
    recipient_type: str
    farmer_count: int
    worker_count: int
    phone_numbers: List[str]


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