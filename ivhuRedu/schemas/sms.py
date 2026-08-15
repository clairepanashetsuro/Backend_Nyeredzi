from typing import List, Optional
from pydantic import BaseModel, Field


class SMSSendRequest(BaseModel):
    alert_type: Optional[str] = None
    message: str
    phone_number: str
    sender_id: Optional[str] = None


class AlertSendRequest(BaseModel):
    alert_type: Optional[str] = None
    message: str
    phone_numbers: List[str] = Field(..., min_length=1)
    sender_id: Optional[str] = None


class OTPSendRequest(BaseModel):
    phone_number: str
    sender_id: Optional[str] = None


class OTPVerifyRequest(BaseModel):
    phone_number: str
    code: str


class OTPVerifyResponse(BaseModel):
    success: bool
    message: str


class SMSPatchRequest(BaseModel):
    status: Optional[str] = None


class SMSPatchResponse(BaseModel):
    success: bool
    updated_count: int


class SMSDeleteResponse(BaseModel):
    success: bool
    deleted_count: int


class SMSLogsResponse(BaseModel):
    logs: List[dict]
    total: int


class SMSHistoryResponse(BaseModel):
    history: List[dict]


class SMSSummaryResponse(BaseModel):
    total_sent: int
    total_failed: int


class SMSCallbackPayload(BaseModel):
    event: str
    message_id: str
    status: str