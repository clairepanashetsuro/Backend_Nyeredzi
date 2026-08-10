from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid

from dependency import get_db, require_roles

from ivhuRedu.models.user import User, UserType

from ivhuRedu.schemas.farmer import (
    FarmerCreate,
    FarmerRead,
    FarmerUpdate,
)

from ivhuRedu.services import farmer as farmer_service


router = APIRouter(
    prefix="/farmers",
    tags=["farmers"],
)




@router.post(
    "/",
    response_model=FarmerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_farmer(
    data: FarmerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserType.EXTENSION_WORKER)
    ),
):
    

    return farmer_service.create_farmer(
        db=db,
        data=data,
    )




@router.get(
    "/{farmer_id}",
    response_model=FarmerRead,
)
def get_farmer(
    farmer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.EXTENSION_WORKER,
            UserType.SUPERVISOR,
            UserType.ADMIN,
        )
    ),
):

    return farmer_service.get_farmer(
        db=db,
        farmer_id=farmer_id,
    )




@router.put(
    "/{farmer_id}",
    response_model=FarmerRead,
)
def update_farmer(
    farmer_id: uuid.UUID,
    data: FarmerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.EXTENSION_WORKER,
            UserType.SUPERVISOR,
            UserType.ADMIN,
        )
    ),
):

    return farmer_service.update_farmer(
        db=db,
        farmer_id=farmer_id,
        data=data.model_dump(
            exclude_unset=True,
        ),
    )




@router.delete(
    "/{farmer_id}",
    status_code=status.HTTP_200_OK,
)
def delete_farmer(
    farmer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.ADMIN,
        )
    ),
):

    farmer_service.delete_farmer(
        db=db,
        farmer_id=farmer_id,
    )