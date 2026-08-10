import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ivhuRedu.models.user import User, UserType

from ivhuRedu.models.extension_worker import (
    ExtensionWorker,
    WorkerAvailabilityStatus,
)

from ivhuRedu.repositories.user import user_repository

from ivhuRedu.schemas.extension_worker import (
    ExtensionWorkerCreate,
)

from ivhuRedu.services.security import hash_password


logger = logging.getLogger(__name__)




def create_extension_worker(
    db: Session,
    data: ExtensionWorkerCreate,
):
    


    existing_user = user_repository.get_by_phone_number(
        db,
        data.phone_number,
    )


    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists.",
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

        # Worker must change temporary password
        # on first login
        must_change_password=True,
    )


    db.add(user)

    db.flush()


    worker = ExtensionWorker(

        user_id=user.id,

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

        db.commit()

        db.refresh(worker)

        return worker


    except IntegrityError:

        db.rollback()

        logger.exception(
            "Failed creating extension worker"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Extension worker could not be created.",
        )





def update_worker_status(
    db: Session,
    worker_id: uuid.UUID,
    availability_status: WorkerAvailabilityStatus,
):
    


    worker = (
        db.query(ExtensionWorker)
        .filter(
            ExtensionWorker.worker_id == worker_id
        )
        .first()
    )


    if not worker:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension worker not found.",
        )


    worker.availability_status = (
        availability_status
    )


    try:

        db.commit()

        db.refresh(worker)

        return worker


    except IntegrityError:

        db.rollback()

        logger.exception(
            "Failed updating extension worker status"
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update extension worker status.",
        )



def get_extension_worker(
    db: Session,
    worker_id: uuid.UUID,
):
    worker = (
        db.query(ExtensionWorker)
        .filter(
            ExtensionWorker.worker_id == worker_id
        )
        .first()
    )

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension worker not found.",
        )

    return worker



def update_extension_worker(
    db: Session,
    worker_id: uuid.UUID,
    data: dict,
):
    worker = get_extension_worker(
        db,
        worker_id,
    )

    user = worker.user

    user_fields = {
        "first_name",
        "last_name",
        "phone_number",
        "email",
    }

    worker_fields = {
        "assigned_ward_name",
        "location_id",
        "availability_status",
    }

    for field, value in data.items():

        if field in user_fields:
            setattr(user, field, value)

        elif field in worker_fields:
            setattr(worker, field, value)

    try:

        db.commit()

        db.refresh(worker)

        return worker

    except IntegrityError:

        db.rollback()

        logger.exception(
            "Failed updating extension worker."
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update extension worker.",
        )



def delete_extension_worker(
    db: Session,
    worker_id: uuid.UUID,
):
    worker = (
        db.query(ExtensionWorker)
        .filter(
            ExtensionWorker.worker_id == worker_id
        )
        .first()
    )

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extension worker not found.",
        )

    user = worker.user

    try:
        db.delete(worker)

        if user:
            db.delete(user)

        db.commit()

        return {
            "message": (
                "Extension worker deleted successfully."
            )
        }

    except Exception:

        db.rollback()

        logger.exception(
            "Failed deleting extension worker."
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete extension worker.",
        )