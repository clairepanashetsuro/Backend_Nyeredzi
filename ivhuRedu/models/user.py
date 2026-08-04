import uuid
import enum
from sqlalchemy import Boolean, Column, String, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ivhuRedu.database import Base


class UserType(str, enum.Enum):
    ADMIN = "admin"
    FARMER = "farmer"
    EXTENSION_WORKER = "extension_worker"
    SUPERVISOR = "supervisor"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    hashed_password = Column(String(150), nullable=True)
    user_type = Column(Enum(UserType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    must_change_password = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    extension_worker = relationship("ExtensionWorker", back_populates="user", uselist=False)
    farmer = relationship("Farmer", back_populates="user", uselist=False)
    sms_alerts = relationship("SMSAlert", back_populates="sent_by", cascade="all, delete-orphan")



