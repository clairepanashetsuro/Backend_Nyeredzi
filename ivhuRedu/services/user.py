"""
services/user.py
-------------------
Business-logic layer for the User entity. This is where we:
  * turn a plain-text password into a bcrypt hash before it is saved,
  * check for a duplicate email/phone number and respond with a clear 409
    instead of letting a raw database error leak out to the client,
  * raise the 404 the router needs whenever a user does not exist.
"""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ivhuRedu.repositories.user import user_repository
from ivhuRedu.schemas.user import UserCreate, UserUpdate
from ivhuRedu.services.security import hash_password

logger = logging.getLogger(__name__)


def get_user(db: Session, id: uuid.UUID):
    """Return one user, or raise 404 if the id does not exist."""
    user = user_repository.get(db, id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def list_users(db: Session):
    """Return every user."""
    return user_repository.get_all(db)


def create_user(db: Session, data: UserCreate):
    """
    Create a new user.

    Steps:
      1. Reject the request early (409 Conflict) if the email or phone
         number is already taken, rather than letting a database
         constraint violation bubble all the way up to the client.
      2. Convert the plain-text password into a bcrypt hash - the raw
         password is never written to the database.
      3. Build the row from only the fields UserCreate declares
         (model_dump), so nothing beyond first_name/last_name/email/
         phone_number/user_type/hashed_password can ever be inserted -
         this is the mass-assignment protection in practice.
    """
    if data.email and user_repository.get_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    if user_repository.get_by_phone_number(db, data.phone_number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists",
        )

    # Drop the plain-text "password" field from the dict that goes to the
    # database - the User model has no such column, only hashed_password.
    payload = data.model_dump(exclude={"password"})
    if data.password:
        payload["hashed_password"] = hash_password(data.password)

    try:
        return user_repository.create(db, payload)
    except IntegrityError:
        # Guards against a race condition (two requests creating the same
        # email/phone at almost the same instant) slipping past the
        # checks above. Log the real detail for the team, show the client
        # only a generic message - errors stay generic, detail goes to
        # server logs.
        db.rollback()
        logger.exception("Integrity error creating user")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User could not be created"
        )


def update_user(db: Session, id: uuid.UUID, data: UserUpdate):
    """Update only the fields that were actually supplied on the request."""
    user = get_user(db, id)

    update_data = data.model_dump(exclude_unset=True, exclude={"password"})
    if data.password:
        update_data["hashed_password"] = hash_password(data.password)

    try:
        return user_repository.update(db, user, update_data)
    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error updating user")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be updated with those values",
        )


def delete_user(db: Session, id: uuid.UUID):
    """Delete a user, raising 404 first if it does not exist."""
    user = get_user(db, id)
    user_repository.delete(db, user)