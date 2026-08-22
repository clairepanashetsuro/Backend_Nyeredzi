import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.password_reset_otp import PasswordResetOTP


class PasswordResetOTPRepository:

    async def get(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> PasswordResetOTP | None:

        return await db.get(
            PasswordResetOTP,
            id,
        )

    async def get_latest_by_user_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> PasswordResetOTP | None:

        result = await db.execute(
            select(PasswordResetOTP)
            .where(
                PasswordResetOTP.user_id == user_id
            )
            .order_by(
                PasswordResetOTP.created_at.desc()
            )
        )

        return result.scalars().first()

    async def get_active_by_user_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> PasswordResetOTP | None:

        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(PasswordResetOTP)
            .where(
                PasswordResetOTP.user_id == user_id,
                PasswordResetOTP.expires_at > now,
            )
            .order_by(
                PasswordResetOTP.created_at.desc()
            )
        )

        return result.scalars().first()

    async def count_recent_by_user_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        minutes: int = 60,
    ) -> int:

        since = (
            datetime.now(timezone.utc)
            - timedelta(minutes=minutes)
        )

        result = await db.execute(
            select(PasswordResetOTP.id)
            .where(
                PasswordResetOTP.user_id == user_id,
                PasswordResetOTP.created_at >= since,
            )
        )

        return len(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        data: dict,
    ) -> PasswordResetOTP:

        otp = PasswordResetOTP(**data)

        db.add(otp)

        await db.commit()
        await db.refresh(otp)

        return otp

    async def update(
        self,
        db: AsyncSession,
        db_obj: PasswordResetOTP,
        data: dict,
    ) -> PasswordResetOTP:

        for field, value in data.items():
            setattr(
                db_obj,
                field,
                value,
            )

        await db.commit()
        await db.refresh(db_obj)

        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        db_obj: PasswordResetOTP,
    ) -> None:

        await db.delete(db_obj)

        await db.commit()

    async def delete_by_user_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:

        await db.execute(
            delete(PasswordResetOTP).where(
                PasswordResetOTP.user_id == user_id
            )
        )

        await db.commit()


password_reset_otp_repository = PasswordResetOTPRepository()