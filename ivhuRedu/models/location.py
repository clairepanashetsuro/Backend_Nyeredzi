import uuid
from sqlalchemy import Column, String, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class Location(Base):
    __tablename__ = "locations"

    location_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(250), nullable=False)
    display_name = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    farmers = relationship("Farmer", back_populates="location")
    extension_workers = relationship("ExtensionWorker", back_populates="location")