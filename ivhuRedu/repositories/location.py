from typing import Optional, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ivhuRedu.models.location import Location
from ivhuRedu.schemas.location import LocationCreate, LocationUpdate

class LocationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, location_data: LocationCreate) -> Location:
        db_location = Location(**location_data.model_dump())
        self.db.add(db_location)
        await self.db.commit()
        await self.db.refresh(db_location)
        return db_location

    async def get_all(self) -> List[Location]:
        result = await self.db.execute(select(Location))
        return result.scalars().all()

    async def get_by_id(self, location_id: uuid.UUID) -> Optional[Location]:
        result = await self.db.execute(select(Location).where(Location.location_id == location_id))
        return result.scalar_one_or_none()

    async def update(self, location_id: uuid.UUID, location_update: LocationUpdate) -> Optional[Location]:
        location = await self.get_by_id(location_id)
        if not location:
            return None
        update_data = location_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(location, field, value)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def delete(self, location_id: uuid.UUID) -> bool:
        location = await self.get_by_id(location_id)
        if not location:
            return False
        await self.db.delete(location)
        await self.db.commit()
        return True