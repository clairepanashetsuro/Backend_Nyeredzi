from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid

from dependency import get_db, require_roles

from ivhuRedu.models.user import User, UserType

from ivhuRedu.schemas.extension_worker import (
    ExtensionWorkerCreate,
    ExtensionWorkerRead,
    ExtensionWorkerStatusUpdate,
    ExtensionWorkerUpdate,

)

from ivhuRedu.services import extension_worker as extension_worker_service


router = APIRouter(
    prefix="/extension-workers",
    tags=["extension-workers"],
)




@router.post(
    "/",
    response_model=ExtensionWorkerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_extension_worker(
    data: ExtensionWorkerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserType.SUPERVISOR)
    ),
):
    

    return extension_worker_service.create_extension_worker(
        db=db,
        data=data,
    )





@router.patch(
    "/{worker_id}/status",
    response_model=ExtensionWorkerRead,
)
def update_extension_worker_status(
    worker_id: uuid.UUID,
    data: ExtensionWorkerStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserType.SUPERVISOR)
    ),
):

    

    return extension_worker_service.update_worker_status(
        db=db,
        worker_id=worker_id,
        availability_status=data.availability_status,
    )  



@router.get(
    "/{worker_id}",
    response_model=ExtensionWorkerRead,
)
def get_extension_worker(
    worker_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.SUPERVISOR,
            UserType.ADMIN,
        )
    ),
):

    return extension_worker_service.get_extension_worker(
        db=db,
        worker_id=worker_id,
    )




@router.put(
    "/{worker_id}",
    response_model=ExtensionWorkerRead,
)
def update_extension_worker(
    worker_id: uuid.UUID,
    data: ExtensionWorkerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.SUPERVISOR,
            UserType.ADMIN,
        )
    ),
):

    return extension_worker_service.update_extension_worker(
        db=db,
        worker_id=worker_id,
        data=data.model_dump(
            exclude_unset=True
        ),
    )   

@router.delete("/{worker_id}")
def delete_extension_worker(
    worker_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return extension_worker_service.delete_extension_worker(
        db=db,
        worker_id=worker_id,
    )