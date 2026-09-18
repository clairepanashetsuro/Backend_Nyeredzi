from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.farmer import Farmer


class FarmerRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_farmer(
        self,
        farmer: Farmer,
    ) -> Farmer:
        self.db.add(farmer)

        await self.db.commit()
        await self.db.refresh(farmer)

        return farmer

    async def get_by_id(
        self,
        farmer_id: UUID,
    ) -> Farmer | None:
        result = await self.db.execute(
            select(Farmer).where(
                Farmer.farmer_id == farmer_id
            )
        )

        return result.scalar_one_or_none()

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> Farmer | None:
        result = await self.db.execute(
            select(Farmer).where(
                Farmer.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    async def get_all(
        self,
    ) -> list[Farmer]:
        result = await self.db.execute(
            select(Farmer)
        )

        return result.scalars().all()

    async def exists_by_user_id(
        self,
        user_id: UUID,
    ) -> bool:
        result = await self.db.execute(
            select(Farmer).where(
                Farmer.user_id == user_id
            )
        )

        return result.scalar_one_or_none() is not None

    async def update_farmer(
        self,
        farmer_id: UUID,
        ward_name: str | None = None,
        location_id: UUID | None = None,
    ) -> Farmer | None:

        farmer = await self.get_by_id(
            farmer_id
        )

        if not farmer:
            return None

        if ward_name is not None:
            farmer.ward_name = ward_name

        if location_id is not None:
            farmer.location_id = location_id

        await self.db.commit()
        await self.db.refresh(farmer)

        return farmer

farmer_repository = FarmerRepository