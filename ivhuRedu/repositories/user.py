from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.user import User
from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.extension_worker import ExtensionWorker


class UserRepository:

    async def get(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> User | None:
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.extension_worker),
                selectinload(User.farmer),
            )
            .where(User.id == id)
        )

        return result.scalar_one_or_none()

    async def get_all(
        self,
        db: AsyncSession,
    ) -> list[User]:
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.extension_worker),
                selectinload(User.farmer),
            )
        )

        return result.scalars().all()

    async def get_all_extension_workers(
        self,
        db: AsyncSession,
    ) -> list[ExtensionWorker]:
        result = await db.execute(
            select(ExtensionWorker)
            .options(
                selectinload(ExtensionWorker.user)
            )
        )

        return result.scalars().all()

    async def get_all_farmers(
        self,
        db: AsyncSession,
    ) -> list[Farmer]:
        result = await db.execute(
            select(Farmer)
            .options(
                selectinload(Farmer.user)
            )
        )

        return result.scalars().all()

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> User | None:
        result = await db.execute(
            select(User).where(
                User.email == email
            )
        )

        return result.scalar_one_or_none()

    async def get_by_phone_number(
        self,
        db: AsyncSession,
        phone_number: str,
    ) -> User | None:
        result = await db.execute(
            select(User).where(
                User.phone_number == phone_number
            )
        )

        return result.scalar_one_or_none()

    async def get_by_user_type(
        self,
        db: AsyncSession,
        user_type,
    ) -> list[User]:
        result = await db.execute(
            select(User).where(
                User.user_type == user_type
            )
        )

        return result.scalars().all()

    async def create(
        self,
        db: AsyncSession,
        data: dict,
    ) -> User:
        user = User(**data)

        db.add(user)

        await db.commit()
        await db.refresh(user)

        return user

    async def update(
        self,
        db: AsyncSession,
        db_obj: User,
        data: dict,
    ) -> User:
        for field, value in data.items():
            setattr(
                db_obj,
                field,
                value,
            )

        await db.commit()
        await db.refresh(db_obj)

        return db_obj


user_repository = UserRepository()