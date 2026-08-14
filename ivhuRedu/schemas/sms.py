from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    SMS = "sms"
    ALERT = "alert"
    OTP = "otp"
    OTP_LOGIN = "otp_login"


class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


class SMSSendRequest(BaseModel):
    phone_number: str
    message: str
    sender_id: Optional[str] = None


class AlertSendRequest(BaseModel):
    phone_numbers: List[str]
    message: str
    sender_id: Optional[str] = None


class OTPSendRequest(BaseModel):
    phone_number: str
    sender_id: Optional[str] = None
    otp_length: Optional[int] = None
    expiry_minutes: Optional[int] = None


class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp_code: str


class OTPVerifyResponse(BaseModel):
    success: bool
    message: str
    phone_number: str


class SMSLogEntry(BaseModel):
    id: str
    type: str
    recipients: str
    message: str
    status: str
    sender_id: str
    ip: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    otp_code: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    external_id: Optional[str] = None
    provider_response: Optional[dict] = None


class SMSLogsResponse(BaseModel):
    logs: List[SMSLogEntry]
    total: int
    page: int
    page_size: int


class SMSPatchRequest(BaseModel):
    status: Optional[str] = None


class SMSDeleteResponse(BaseModel):
    deleted: int
    message: str
    filters_applied: dict


class SMSPatchResponse(BaseModel):
    updated: int
    message: str
    filters_applied: dict


class SMSHistoryResponse(BaseModel):
    history: List[SMSLogEntry]
    total: int


class SMSSummaryResponse(BaseModel):
    total_sent: int
    total_failed: int
    total_pending: int
    total_delivered: int
    total_expired: int
    total_otp: int
    total_alerts: int
    total_sms: int


class SMSCallbackPayload(BaseModel):
    message_id: str
    status: str
    phone_number: Optional[str] = None
    delivered_at: Optional[datetime] = None
    failure_reason: Optional[str] = None