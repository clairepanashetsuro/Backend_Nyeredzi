from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.extension_worker import ExtensionWorker


class ExtensionWorkerRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_extension_worker(
        self,
        extension_worker: ExtensionWorker,
    ) -> ExtensionWorker:
        self.db.add(extension_worker)

        await self.db.commit()
        await self.db.refresh(extension_worker)

        return extension_worker

    async def get_by_id(
        self,
        extension_worker_id: UUID,
    ) -> ExtensionWorker | None:
        result = await self.db.execute(
            select(ExtensionWorker).where(
                ExtensionWorker.extension_worker_id == extension_worker_id
            )
        )

        return result.scalar_one_or_none()

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> ExtensionWorker | None:
        result = await self.db.execute(
            select(ExtensionWorker).where(
                ExtensionWorker.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    async def get_all(
        self,
    ) -> list[ExtensionWorker]:
        result = await self.db.execute(
            select(ExtensionWorker)
        )

        return result.scalars().all()

    async def exists_by_user_id(
        self,
        user_id: UUID,
    ) -> bool:
        result = await self.db.execute(
            select(ExtensionWorker).where(
                ExtensionWorker.user_id == user_id
            )
        )

        return result.scalar_one_or_none() is not None

    async def update_extension_worker(
        self,
        extension_worker_id: UUID,
        ward_name: str | None = None,
        location_id: UUID | None = None,
    ) -> ExtensionWorker | None:

        extension_worker = await self.get_by_id(
            extension_worker_id
        )

        if not extension_worker:
            return None

        if ward_name is not None:
            extension_worker.ward_name = ward_name

        if location_id is not None:
            extension_worker.location_id = location_id

        await self.db.commit()
        await self.db.refresh(extension_worker)

        return extension_worker

worker_repository = ExtensionWorkerRepository