

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ivhuRedu.dependencies import ensure_self_or_privileged, get_current_user, get_db, require_roles
from ivhuRedu.models.user import User, UserType
from ivhuRedu.schemas.user import UserCreate, UserRead, UserUpdate
from ivhuRedu.services import user as user_service

router = APIRouter(prefix="/users", tags=["users"])





@router.post("/", response_model=UserRead)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if current_user.user_type == UserType.ADMIN:
        if data.user_type != UserType.SUPERVISOR:
            raise HTTPException(
                status_code=403,
                detail="Admins can only create supervisors."
            )

    
    elif current_user.user_type == UserType.SUPERVISOR:
        if data.user_type != UserType.EXTENSION_WORKER:
            raise HTTPException(
                status_code=403,
                detail="Supervisors can only create extension workers."
            )


    elif current_user.user_type == UserType.EXTENSION_WORKER:
        if data.user_type != UserType.FARMER:
            raise HTTPException(
                status_code=403,
                detail="Extension workers can only create farmers."
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Not authorized."
        )

    return user_service.create_user(db, data)


@router.get(
    "/",
    response_model=List[UserRead],
    dependencies=[Depends(require_roles(UserType.ADMIN, UserType.SUPERVISOR))],
)
def list_users(db: Session = Depends(get_db)):
    """GET /users - admin or supervisor only: list every user."""
    return user_service.list_users(db)


@router.get("/{id}", response_model=UserRead)
def get_user(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /users/{id} - the user themselves, or an admin/district_supervisor."""
    ensure_self_or_privileged(id, current_user)
    return user_service.get_user(db, id)


@router.put("/{id}", response_model=UserRead)
def update_user(
    id: uuid.UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    ensure_self_or_privileged(id, current_user)

    if data.user_type is not None and current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can change a user's role",
        )

    return user_service.update_user(db, id, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserType.ADMIN))],
)
def delete_user(id: uuid.UUID, db: Session = Depends(get_db)):
    """DELETE /users/{id} - admin only."""
    user_service.delete_user(db, id)