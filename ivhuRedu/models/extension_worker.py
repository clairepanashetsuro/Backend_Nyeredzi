import enum
import uuid
from sqlalchemy import Column, Enum, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ivhuRedu.database import Base

class WorkerAvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ON_LEAVE = "on_leave"


class ExtensionWorker(Base):
    __tablename__ = "extension_workers"

    worker_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    hashed_ussd_pincode = Column(String(255), nullable=False)
    assigned_ward_name = Column(String(100), nullable=False)

    availability_status = Column(
        Enum(WorkerAvailabilityStatus, values_callable=lambda obj: [e.value for e in obj]), 
        nullable=False, 
        default=WorkerAvailabilityStatus.AVAILABLE
    )
    
    # Corrected singular table name
    location_id = Column(UUID(as_uuid=True), ForeignKey("location.location_id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="extension_worker")
    farmer_requests = relationship("FarmerRequest", back_populates="extension_worker")
    field_reports = relationship("FieldReport", back_populates="extension_worker")
    
    location = relationship(
        "Location", 
        back_populates="extension_workers",
        primaryjoin="ExtensionWorker.location_id == Location.location_id"
    )

