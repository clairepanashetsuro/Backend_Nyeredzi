from ivhuRedu.database import Base
import enum
import uuid

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Float, Text, Index
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text , Float
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func



class RequestType(str, enum.Enum):
    VISIT_REQUEST = "visit_request"
    ADVISE_REQUEST = "advice_request"
    LAND_DEGRADATION_REPORT = "land_degradation_report"


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class FarmerRequest(Base):
    __tablename__ = "farmer_requests"

    request_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_worker_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    phone_number = Column(String, nullable=False)
    request_type = Column(String, nullable=False)
    ussd_session_id = Column(String, nullable=True)
    ussd_input_text = Column(Integer, nullable=True)
    distance_in_meters = Column(Float, nullable=True)
    sync_status = Column(String, default="PENDING_SYNC", nullable=True)
    status = Column(String, nullable=False, server_default="PENDING")
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

    farmer_id = Column(PG_UUID(as_uuid=True), ForeignKey("farmers.farmer_id", ondelete="SET NULL"), nullable=True)
    worker_id = Column(PG_UUID(as_uuid=True), ForeignKey("extension_workers.worker_id", ondelete="SET NULL"), nullable=True)
    request_type = Column(Enum(RequestType, name="request_type"), nullable=False)
    ussd_input_text = Column(Text, nullable=True)
    distance_m = Column(Float, nullable=True)
    # status = Column(Enum(RequestStatus, name="request_status"), nullable=False, default=RequestStatus.PENDING, server_default=RequestStatus.PENDING.value)
    status = Column(Enum(RequestStatus), default="PENDING", nullable=False)



    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    farmer = relationship("Farmer", back_populates="requests")
    field_reports = relationship("FieldReport", back_populates="farmer_request")
    extension_worker = relationship("ExtensionWorker", back_populates="farmer_requests")
