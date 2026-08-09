import enum
import uuid

from sqlalchemy import Column, DateTime, String, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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
    worker_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_type = Column(String, nullable=False)
    ussd_input_text = Column(Float, nullable=True)
    distance_m = Column(Float, nullable=True)
    sync_status = Column(String, default="pending_sync", nullable=True)
    request_status = Column(String, nullable=False, server_default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
