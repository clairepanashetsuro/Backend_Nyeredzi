import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependency import (
    ensure_self_or_privileged,
    get_db,
    require_password_changed,
    require_roles,
)
from ivhuRedu.models.user import User, UserType
from ivhuRedu.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from ivhuRedu.services import user as user_service

# FIX: Removed local prefix and tags to stop Swagger UI page duplication
router = APIRouter()

@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: UserCreate,
    user_type: UserType = UserType.SUPERVISOR,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserType.ADMIN)
    ),
):
    return await user_service.create_user(
        db=db,
        data=data,
        user_type=user_type,
    )

@router.get(
    "/",
    response_model=List[UserRead],
    dependencies=[
        Depends(
            require_roles(
                UserType.ADMIN,
                UserType.SUPERVISOR,
            )
        )
    ],
)
async def list_users(
    db: AsyncSession = Depends(get_db),
):
    return await user_service.list_users(db)

@router.get(
    "/{id}",
    response_model=UserRead,
)
async def get_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_password_changed
    ),
):
    ensure_self_or_privileged(
        id,
        current_user,
    )
    return await user_service.get_user(
        db,
        id,
    )

@router.put(
    "/{id}",
    response_model=UserRead,
)
async def update_user(
    id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_password_changed
    ),
):
    ensure_self_or_privileged(
        id,
        current_user,
    )
    return await user_service.update_user(
        db,
        id,
        data,
    )

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(
            require_roles(
                UserType.ADMIN
            )
        )
    ],
)
async def delete_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await user_service.delete_user(
        db,
        id,
    )
