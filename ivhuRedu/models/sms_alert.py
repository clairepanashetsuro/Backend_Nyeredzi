from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class SMSAlert(Base):
    __tablename__ = "sms_alerts"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    sent_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipients_count = Column(Integer, nullable=False, default=0)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    
    sent_by = relationship(
        "User", 
        primaryjoin="and_(SMSAlert.sent_by_user_id == User.id, User.role == 'supervisor')"
    )
