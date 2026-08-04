import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)

from sqlalchemy.dialects.postgresql import UUID

from ivhuRedu.database import Base


class OTPPurpose(str, enum.Enum):
    FIRST_LOGIN = "first_login"
    PASSWORD_RESET = "password_reset"


class OTP(Base):
    __tablename__ = "otp_codes"

    otp_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    code = Column(String(6), nullable=False)

    purpose = Column(
        Enum(OTPPurpose),
        nullable=False,
    )

    attempts = Column(
        Integer,
        default=0,
    )

    used = Column(
        Boolean,
        default=False,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )