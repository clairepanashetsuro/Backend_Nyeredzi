import uuid
import enum
from sqlalchemy import Boolean, Column, String, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


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
    user_type = Column(Enum(UserType,values_callable=lambda enum_class: [e.value for e in enum_class],name="usertype",),nullable=False,)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    must_change_password = Column(Boolean, default=True, server_default="true",nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)


    extension_worker = relationship("ExtensionWorker", back_populates="user", uselist=False)
    farmer = relationship("Farmer", back_populates="user", uselist=False)
    requests = relationship("FarmerRequest", foreign_keys="FarmerRequest.farmer_id", back_populates="farmer")
    assigned_requests = relationship("FarmerRequest", foreign_keys="FarmerRequest.assigned_worker_id", back_populates="assigned_worker")

