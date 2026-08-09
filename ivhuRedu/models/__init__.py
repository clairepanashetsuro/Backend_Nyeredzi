from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from ivhuRedu.models.user import User

__all__ = [
    "Base",
    "User",
]
