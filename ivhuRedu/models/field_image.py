from database import Base
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class FieldImage(Base):
    __tablename__ = "field_images"

    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True),ForeignKey("field_reports.report_id",ondelete="CASCADE",),nullable=False,)
    image_url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    field_report = relationship("FieldReport", back_populates="images")