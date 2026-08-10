import enum
import uuid

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Float, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class RequestType(str, enum.Enum):
    Visit_Request = "visit_request"
    Advice_Request = "advice_request"
    Land_Degradation_Report = "land_degradation_report"


class RequestStatus(str, enum.Enum):
    Pending = "pending"
    Assigned = "assigned"
    Resolved = "resolved"
    Cancelled = "cancelled"


class FarmerRequest(Base):
    __tablename__ = "farmer_requests"

    request_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_worker_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    phone_number = Column(String, nullable=False)
    request_type = Column(String, nullable=False)
    
    ussd_session_id = Column(String, nullable=True)
    ussd_input_text = Column(Integer, nullable=True)
    
    distance_m = Column(Float, nullable=True)
    sync_status = Column(String, default="pending_sync", nullable=True)
    status = Column(String, nullable=False, server_default="pending")
    
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    farmer = relationship("User", foreign_keys=[farmer_id], back_populates="requests")
    assigned_worker = relationship("User", foreign_keys=[assigned_worker_id], back_populates="assigned_requests")
    
    __table_args__ = (
        Index("ix_farmer_requests_phone_number", "phone_number"),
        Index("ix_farmer_requests_status", "status"),
    )