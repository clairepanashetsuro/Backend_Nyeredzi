import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from ivhuRedu.repositories.location import LocationRepository
from ivhuRedu.schemas.location import LocationCreate, LocationUpdate, LocationGeocodeRequest
from ivhuRedu.config import LOCATIONIQ_API_KEY, LOCATIONIQ_URL

class LocationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LocationRepository(db)

    async def create(self, location_data: LocationCreate):
        return await self.repo.create(location_data)

    async def get_all(self) -> List:
        return await self.repo.get_all()

    async def get_by_id(self, location_id: UUID) -> Optional:
        return await self.repo.get_by_id(location_id)

    async def update(self, location_id: UUID, location_update: LocationUpdate):
        return await self.repo.update(location_id, location_update)

    async def delete(self, location_id: UUID) -> bool:
        return await self.repo.delete(location_id)

    async def geocode_and_create(self, request: LocationGeocodeRequest):
        try:
            params = {
                "key": LOCATIONIQ_API_KEY,
                "q": request.address,
                "format": "json",
                "limit": 1
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(LOCATIONIQ_URL, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    location_data = LocationCreate(
                        latitude=float(data[0]["lat"]),
                        longitude=float(data[0]["lon"]),
                        address=request.address,
                        display_name=data[0].get("display_name")
                    )
                    return await self.repo.create(location_data)
        except Exception:
            pass

        location_data = LocationCreate(
            latitude=-17.8252,
            longitude=31.0335,
            address=request.address,
            display_name=request.address + " (mock geocode)"
        )
        return await self.repo.create(location_data)
