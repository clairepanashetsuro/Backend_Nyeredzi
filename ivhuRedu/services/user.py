import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ivhuRedu.models.user import User, UserType
from ivhuRedu.repositories.user import user_repository
from ivhuRedu.schemas.user import UserCreate, UserUpdate
from ivhuRedu.services.security import hash_password


logger = logging.getLogger(__name__)




def get_user(
    db: Session,
    id: uuid.UUID,
):
    """
    Return one user or raise 404.
    """

    user = user_repository.get(
        db,
        id,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user




def list_users(
    db: Session,
):
    """
    Return all users.
    """

    return user_repository.get_all(db)




def create_user(
    db: Session,
    data: UserCreate,
    user_type: UserType,
):
    
    

    if data.email and user_repository.get_by_email(
        db,
        data.email,
    ):

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    

    if user_repository.get_by_phone_number(
        db,
        data.phone_number,
    ):

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists",
        )

   

    payload = data.model_dump(
        exclude={"password"}
    )

    

    payload["user_type"] = user_type

   

    if data.password:

        payload["hashed_password"] = hash_password(
            data.password
        )

   

    payload["must_change_password"] = True

   

    try:

        return user_repository.create(
            db,
            payload,
        )

    except IntegrityError:

        db.rollback()

        logger.exception(
            "Integrity error creating user"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be created",
        )




def update_user(
    db: Session,
    id: uuid.UUID,
    data: UserUpdate,
):
    

    user = get_user(
        db,
        id,
    )

  

    update_data = data.model_dump(
        exclude_unset=True,
        exclude={"password"},
    )

   

    if data.password:

        update_data["hashed_password"] = hash_password(
            data.password
        )

        update_data["must_change_password"] = False

    

    try:

        return user_repository.update(
            db,
            user,
            update_data,
        )

    except IntegrityError:

        db.rollback()

        logger.exception(
            "Integrity error updating user"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be updated with those values",
        )




def delete_user(
    db: Session,
    id: uuid.UUID,
):
    """
    Delete an existing user.
    """

    user = get_user(
        db,
        id,
    )

    user_repository.delete(
        db,
        user,
    )

    return {
        "message": "User deleted successfully"
    }

