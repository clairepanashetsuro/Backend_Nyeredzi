import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ivhuRedu.models.user import User, UserType
from ivhuRedu.models.extension_worker import (
    ExtensionWorker,
    WorkerAvailabilityStatus,
)

from ivhuRedu.repositories.user import user_repository

from ivhuRedu.schemas.extension_worker import (
    ExtensionWorkerCreate,
)

from ivhuRedu.services.security import (
    hash_password,
)


logger = logging.getLogger(__name__)


async def create_extension_worker(
    db: AsyncSession,
    data: ExtensionWorkerCreate,
):
    existing_user = await user_repository.get_by_phone_number(
        db,
        data.phone_number,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists.",
        )

    if data.email:
        existing_email = await user_repository.get_by_email(
            db,
            data.email,
        )

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        phone_number=data.phone_number,
        email=data.email,
        hashed_password=await hash_password(
            data.password
        ),
        user_type=UserType.EXTENSION_WORKER,
        must_change_password=True,
    )

    db.add(user)

    await db.flush()

    worker = ExtensionWorker(
        user_id=user.id,
        hashed_ussd_pincode=await hash_password(
            data.ussd_pincode
        ),
        assigned_ward_name=data.assigned_ward_name,
        location_id=data.location_id,
        availability_status=WorkerAvailabilityStatus.AVAILABLE,
    )

    db.add(worker)

    try:
        await db.commit()

        return await get_extension_worker(
            db,
            worker.worker_id,
        )

    except IntegrityError:
        await db.rollback()

        logger.exception(
            "Failed creating extension worker"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Extension worker could not be created.",
        )


async def update_worker_status(
    db: AsyncSession,
    worker_id: uuid.UUID,
    availability_status: WorkerAvailabilityStatus,
):
    result = await db.execute(
        select(ExtensionWorker).where(
            ExtensionWorker.worker_id == worker_id
        )
    )

    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension worker not found.",
        )

    worker.availability_status = availability_status

    try:
        await db.commit()

        await db.refresh(worker)

        return worker

    except IntegrityError:
        await db.rollback()

        logger.exception(
            "Failed updating extension worker status"
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update extension worker status.",
        )


async def get_extension_worker(
    db: AsyncSession,
    worker_id: uuid.UUID,
):
    result = await db.execute(
        select(ExtensionWorker)
        .options(
            selectinload(
                ExtensionWorker.user
            )
        )
        .where(
            ExtensionWorker.worker_id == worker_id
        )
    )

    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension worker not found.",
        )

    return worker


async def update_extension_worker(
    db: AsyncSession,
    worker_id: uuid.UUID,
    data: dict,
    current_user: User,
):
    worker = await get_extension_worker(
        db,
        worker_id,
    )

    user = worker.user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension worker user not found.",
        )

    is_privileged = current_user.user_type in {
        UserType.SUPERVISOR,
        UserType.ADMIN,
    }

    is_self = (
        current_user.user_type == UserType.EXTENSION_WORKER
        and worker.user_id == current_user.id
    )

    if not is_privileged and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own extension worker details.",
        )

    personal_fields = {
        "first_name",
        "last_name",
        "phone_number",
        "email",
    }

    restricted_worker_fields = {
        "assigned_ward_name",
        "location_id",
    }

    for field, value in data.items():
        if field in personal_fields:
            setattr(
                user,
                field,
                value,
            )

        elif field == "password":
            user.hashed_password = await hash_password(
                value
            )
            user.must_change_password = False

        elif field == "ussd_pincode":
            worker.hashed_ussd_pincode = await hash_password(
                value
            )

        elif field in restricted_worker_fields:
            if not is_privileged:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have permission to update {field}.",
                )

            setattr(
                worker,
                field,
                value,
            )

        elif field == "availability_status":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Availability status must be updated through the status endpoint.",
            )

    try:
        await db.commit()

        return await get_extension_worker(
            db,
            worker_id,
        )

    except IntegrityError:
        await db.rollback()

        logger.exception(
            "Failed updating extension worker"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update extension worker.",
        )


async def delete_extension_worker(
    db: AsyncSession,
    worker_id: uuid.UUID,
):
    result = await db.execute(
        select(ExtensionWorker)
        .options(
            selectinload(
                ExtensionWorker.user
            )
        )
        .where(
            ExtensionWorker.worker_id == worker_id
        )
    )

    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension worker not found.",
        )

    user = worker.user

    try:
        await db.delete(worker)

        if user:
            await db.delete(user)

        await db.commit()

        return {
            "message": "Extension worker deleted successfully."
        }

    except IntegrityError:
        await db.rollback()

        logger.exception(
            "Failed deleting extension worker"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not delete extension worker.",
        )