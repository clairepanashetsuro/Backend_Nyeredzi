import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
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
    farmer_id = Column(PG_UUID(as_uuid=True), ForeignKey("farmers.farmer_id", ondelete="SET NULL"), nullable=True)
    worker_id = Column(PG_UUID(as_uuid=True),ForeignKey("extension_workers.worker_id", ondelete="SET NULL"),nullable=True,)
    request_type = Column(Enum(RequestType, name="request_type"), nullable=False)
    ussd_input_text = Column(Text, nullable=True)
    distance_m = Column(Integer, nullable=True)
    request_status = Column(Enum(RequestStatus, name="request_status"), nullable=False, server_default="pending")
    

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    farmer = relationship("Farmer", back_populates="requests")
    assigned_worker = relationship("ExtensionWorker", back_populates="farmer_requests")