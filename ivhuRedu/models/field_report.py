import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class IssueType(str, enum.Enum):
    LAND_DEGRADATION = "land_degradation"
    PEST_OUTBREAK = "pest_outbreak"
    CROP_FAILURE = "crop_failure"


class SyncStatus(str, enum.Enum):
    PENDING_SYNC = "pending_sync"
    SYNCED = "synced"

class FieldReport(Base):
    __tablename__ = "field_reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    worker_id = Column(UUID(as_uuid=True), ForeignKey("extension_workers.worker_id"), nullable=False)
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=True)
    related_request_id = Column(UUID(as_uuid=True), ForeignKey("farmer_requests.request_id"), nullable=True)

    issue_type = Column(Enum(IssueType), nullable=True)
    report_details = Column(Text, nullable=True)
    ussd_description = Column(Text, nullable=True)
    sync_status = Column(Enum(SyncStatus), nullable=False, server_default="pending_sync")

    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    synced_at = Column(DateTime(timezone=True), nullable=True)

    extension_worker = relationship("ExtensionWorker", back_populates="field_reports")
    farmer = relationship("Farmer", back_populates="field_reports")
    farmer_request = relationship("FarmerRequest", back_populates="field_reports")
    images = relationship("FieldImage", back_populates="field_report",cascade="all, delete-orphan",)