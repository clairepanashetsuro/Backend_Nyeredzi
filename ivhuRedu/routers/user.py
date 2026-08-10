
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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


router = APIRouter(
    prefix="/users",
    tags=["users"],
)




@router.post(
    "/",
    response_model=UserRead,
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed),
):
  

    if current_user.user_type == UserType.ADMIN:

        assigned_role = UserType.SUPERVISOR

    elif current_user.user_type == UserType.SUPERVISOR:

        assigned_role = UserType.EXTENSION_WORKER

    elif current_user.user_type == UserType.EXTENSION_WORKER:

        assigned_role = UserType.FARMER

    else:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create users.",
        )

  

    return user_service.create_user(
        db=db,
        data=data,
        user_type=assigned_role,
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
def list_users(
    db: Session = Depends(get_db),
):
    return user_service.list_users(db)




@router.get(
    "/{id}",
    response_model=UserRead,
)
def get_user(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed),
):
    ensure_self_or_privileged(
        id,
        current_user,
    )

    return user_service.get_user(
        db,
        id,
    )




@router.put(
    "/{id}",
    response_model=UserRead,
)
def update_user(
    id: uuid.UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed),
):
    ensure_self_or_privileged(
        id,
        current_user,
    )



    return user_service.update_user(
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
def delete_user(
    id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return user_service.delete_user(
        db,
        id,
    )

