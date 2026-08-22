import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


from database import Base


class Farmer(Base):
    __tablename__ = "farmers"

    farmer_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    ward_name = Column(String(100), nullable=False)
    primary_crop = Column (String (50), nullable = True)
    location_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("location.location_id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="farmer")
    location = relationship("Location", back_populates="farmers")
    requests = relationship("FarmerRequest", back_populates="farmer")
    
    field_reports = relationship("FieldReport", back_populates="farmer")
