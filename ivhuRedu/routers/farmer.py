import uuid

from fastapi import APIRouter, Depends, status

from sqlalchemy.ext.asyncio import AsyncSession

from dependency import get_db, require_roles

from ivhuRedu.models.user import User, UserType

from ivhuRedu.schemas.farmer import (
    FarmerCreate,
    FarmerRead,
    FarmerUpdate,
)

from ivhuRedu.repositories.user import user_repository

from ivhuRedu.services import farmer as farmer_service


router = APIRouter(
    prefix="/farmers",
    tags=["Farmers"],
)


@router.post(
    "/",
    response_model=FarmerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_farmer(
    data: FarmerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.EXTENSION_WORKER
        )
    ),
):
    return await farmer_service.create_farmer(
        db=db,
        data=data,
    )


@router.get(
    "/",
    response_model=list[FarmerRead],
)
async def get_farmers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.SUPERVISOR,
            UserType.ADMIN,
            UserType.EXTENSION_WORKER,

        )
    ),
):
    return await user_repository.get_all_farmers(
        db
    )


@router.get(
    "/{farmer_id}",
    response_model=list[FarmerRead],
)
async def get_farmer(
    farmer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.EXTENSION_WORKER,
            UserType.SUPERVISOR,
            UserType.ADMIN,
        )
    ),
):
    return await farmer_service.get_farmer(
        db=db,
        farmer_id=farmer_id,
    )


@router.put(
    "/{farmer_id}",
    response_model=FarmerRead,
)
async def update_farmer(
    farmer_id: uuid.UUID,
    data: FarmerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.EXTENSION_WORKER,
            UserType.SUPERVISOR,
            UserType.ADMIN,
        )
    ),
):
    return await farmer_service.update_farmer(
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
async def delete_farmer(
    farmer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserType.ADMIN,
            UserType.EXTENSION_WORKER,

        )
    ),
):
    return await farmer_service.delete_farmer(
        db=db,
        farmer_id=farmer_id,
    )