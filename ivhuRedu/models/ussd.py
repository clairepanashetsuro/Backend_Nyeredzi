from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class USSDSession(Base):
    __tablename__ = "ussd_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    current_step = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
