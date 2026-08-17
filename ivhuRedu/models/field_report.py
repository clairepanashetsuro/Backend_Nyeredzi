from ivhuRedu.database import Base
import enum
import uuid
from sqlalchemy import Column, DateTime, Enum as SqlEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class IssueType(str, enum.Enum):
    LAND_DEGRADATION = "Land Degradation"
    PEST_OUTBREAK = "Pest Outbreak"
    CROP_FAILURE = "Crop Failure"

class SyncStatus(str, enum.Enum):
    PENDING_SYNC = "PENDING_SYNC"
    SYNCED = "synced"

class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "completed"
    ERROR = "error"

class FieldReport(Base):
    __tablename__ = "field_reports"
    
    report_id = Column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )

    worker_id = Column(PG_UUID(as_uuid=True), ForeignKey("extension_workers.worker_id", ondelete="SET NULL"), nullable=False)
    farmer_id = Column(PG_UUID(as_uuid=True), ForeignKey("farmers.farmer_id", ondelete="SET NULL"), nullable=True)
    related_request_id = Column(PG_UUID(as_uuid=True), ForeignKey("farmer_requests.request_id", ondelete="SET NULL"), nullable=True)

    issue_type = Column(SqlEnum(IssueType, name="issue_type_enum"), nullable=True)
    report_details = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    description_type = Column(Text, nullable=False)
    
    ussd_description = Column(Text, nullable=True)
    ussd_info = Column(Text, nullable=True)

    sync_status = Column(
        SqlEnum(SyncStatus, name="sync_status_enum"), 
        nullable=False, 
        default=SyncStatus.PENDING_SYNC,
        server_default="PENDING_SYNC"
    )
    status = Column(
        SqlEnum(StatusEnum, name="status_enum"),
        nullable=False,
        default=StatusEnum.PENDING,
    )

    timestamp_captured = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    timestamp_synced = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    extension_worker = relationship("ExtensionWorker", back_populates="field_reports")
    farmer = relationship("Farmer", back_populates="field_reports")
    farmer_request = relationship("FarmerRequest", back_populates="field_reports")
    images = relationship("FieldImage", back_populates="field_report", cascade="all, delete-orphan")
