
import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.user import UserType
from ivhuRedu.repositories.user import user_repository
from ivhuRedu.schemas.user import UserCreate, UserUpdate
from ivhuRedu.services.security import hash_password


logger = logging.getLogger(__name__)


async def get_user(
    db: AsyncSession,
    id: uuid.UUID,
):
    """
    Return one user or raise 404.
    """

    user = await user_repository.get(
        db,
        id,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def list_users(
    db: AsyncSession,
):
    """
    Return all users.
    """

    return await user_repository.get_all(db)


async def create_user(
    db: AsyncSession,
    data: UserCreate,
    user_type: UserType,
):
    if data.email:
        existing_email = (
            await user_repository.get_by_email(
                db,
                data.email,
            )
        )

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )


    existing_phone = (
        await user_repository.get_by_phone_number(
            db,
            data.phone_number,
        )
    )

    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists",
        )


    if user_type == UserType.SUPERVISOR and not data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required when creating a supervisor.",
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
    else:
        payload["hashed_password"] = None
        payload["must_change_password"] = False

    try:
        return await user_repository.create(
            db,
            payload,
        )

    except IntegrityError:
        await db.rollback()

        logger.exception(
            "Integrity error creating user"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be created",
        )


async def update_user(
    db: AsyncSession,
    id: uuid.UUID,
    data: UserUpdate,
):
    user = await get_user(
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


        update_data["must_change_password"] = True

    try:
        return await user_repository.update(
            db,
            user,
            update_data,
        )

    except IntegrityError:
        await db.rollback()

        logger.exception(
            "Integrity error updating user"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User could not be updated with those values",
        )


async def delete_user(
    db: AsyncSession,
    id: uuid.UUID,
):
    """
    Delete an existing user.
    """

    user = await get_user(
        db,
        id,
    )

    await user_repository.delete(
        db,
        user,
    )

    return {
        "message": "User deleted successfully"
    }

