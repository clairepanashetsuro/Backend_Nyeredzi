import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependency import get_db, require_roles

from ivhuRedu.models.user import User, UserType

from ivhuRedu.schemas.extension_worker import (
    ExtensionWorkerCreate,
    ExtensionWorkerRead,
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
async def create_extension_worker(
    data: ExtensionWorkerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserType.SUPERVISOR)
    ),
):
    return await extension_worker_service.create_extension_worker(
        db,
        data,
    )