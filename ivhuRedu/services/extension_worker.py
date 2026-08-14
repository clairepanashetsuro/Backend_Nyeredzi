
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


        hashed_password=hash_password(
            data.password
        ),

        user_type=UserType.EXTENSION_WORKER,



        must_change_password=True,
    )

    db.add(user)

    await db.flush()


    worker = ExtensionWorker(
        user_id=user.id,

        # USSD PIN must also be hashed
        hashed_ussd_pincode=hash_password(
            data.ussd_pincode
        ),

        assigned_ward_name=data.assigned_ward_name,

        location_id=data.location_id,

        availability_status=(
            WorkerAvailabilityStatus.AVAILABLE
        ),
    )

    db.add(worker)

    try:
        await db.commit()

        await db.refresh(worker)

        return worker

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

    # Fields belonging to the User table
    user_fields = {
        "first_name",
        "last_name",
        "phone_number",
        "email",
    }

    # Fields belonging to ExtensionWorker table
    worker_fields = {
        "assigned_ward_name",
        "location_id",
        "availability_status",
    }

    for field, value in data.items():



        if field in user_fields:

            setattr(
                user,
                field,
                value,
            )



        elif field == "password":

            user.hashed_password = hash_password(
                value
            )


            user.must_change_password = True



        elif field in worker_fields:

            setattr(
                worker,
                field,
                value,
            )



        elif field == "ussd_pincode":

            worker.hashed_ussd_pincode = hash_password(
                value
            )

    try:
        await db.commit()

        await db.refresh(worker)

        return worker

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
        # Delete worker first because it references the user.
        await db.delete(worker)

        # Then delete the associated user.
        if user:
            await db.delete(user)

        await db.commit()

        return {
            "message": (
                "Extension worker deleted successfully."
            )
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
