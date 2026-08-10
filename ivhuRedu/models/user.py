import uuid
import enum
from sqlalchemy import Column, String, DateTime, Enum, func
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
    user_type = Column(Enum(UserType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # farmer = relationship("Farmer", back_populates="user", uselist=False)
    # extension_worker = relationship("ExtensionWorker", back_populates="user", uselist=False)


