import math
import os
from typing import Optional
import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from uuid import UUID
from ivhuRedu.models.extension_worker import ExtensionWorker
from ivhuRedu.models.location import Location
from ivhuRedu.models.user import User
from ivhuRedu.models.farmer import Farmer
from ivhuRedu.schemas.location import LocationCreate, LocationUpdate, LocationGeocodeRequest




class LocationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _get_api_key(self) -> str:
        api_key = os.getenv("LOCATIONIQ_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LOCATIONIQ_API_KEY not configured in .env"
            )
        return api_key

    async def _locationiq_request(self, endpoint: str, params: dict):
        api_key = self._get_api_key()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://us1.locationiq.com/v1/{endpoint}.php",
                params={"key": api_key, **params}
            )
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict) and "error" in data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"])
        return data

    async def create(self, location: LocationCreate):
        db_location = Location(**location.dict())
        self.db.add(db_location)
        await self.db.commit()
        await self.db.refresh(db_location)
        return db_location

    async def get_all(self, skip: int = 0, limit: int = 100):
        result = await self.db.execute(select(Location).offset(skip).limit(limit))
        return result.scalars().all()

    async def get_by_id(self, location_id: UUID):
        result = await self.db.execute(select(Location).where(Location.location_id == location_id))
        location = result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        return location

    async def update(self, location_id: UUID, location_update: LocationUpdate):
        location = await self.get_by_id(location_id)
        for field, value in location_update.dict(exclude_unset=True).items():
            setattr(location, field, value)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def delete(self, location_id: UUID):
        location = await self.get_by_id(location_id)
        await self.db.delete(location)
        await self.db.commit()
        return None

    async def search(
        self,
        q: Optional[str] = None,
        ward: Optional[str] = None,
    ):
        query = select(Location)

        if q:
            pattern = f"%{q}%"
            query = query.where(
                or_(
                    Location.address.ilike(pattern),
                    Location.display_name.ilike(pattern),
                )
            )

        if ward:
            pattern = f"%{ward}%"
            query = query.where(
                Location.address.ilike(pattern)
            )

        result = await self.db.execute(query)

        return result.scalars().all()

    async def geocode_and_create(
        self,
        request: LocationGeocodeRequest,
    ):
        data = await self._locationiq_request(
            "search",
            {
                "q": request.address,
                "format": "json",
                "limit": 1,
            },
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found",
            )

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])

        location_data = LocationCreate(
            address=request.address,
            display_name=data[0].get(
                "display_name"
            ),
            latitude=lat,
            longitude=lon,
        )

        return await self.create(location_data)

    async def autocomplete_address(self, q: str):
        if len(q) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Query must be at least 2 characters"
            )
        data = await self._locationiq_request("autocomplete", {"q": q, "limit": 5})
        return {"suggestions": data}

    async def reverse_geocode(self, lat: float, lon: float):
        return await self._locationiq_request(
            "reverse",
            {"lat": lat, "lon": lon, "format": "json"}
        )

    async def find_nearby_workers(self, lat: float, lng: float, radius_km: float, skill: Optional[str] = None):
       

        query = (
            select(ExtensionWorker, Location, User)
            .join(Location, ExtensionWorker.location_id == Location.location_id)
            .join(User, ExtensionWorker.user_id == User.id)
        )
        result = await self.db.execute(query)
        rows = result.all()

        nearby = []
        for worker, location, user in rows:
            if location.latitude is None or location.longitude is None:
                continue
            distance = self._haversine(lat, lng, location.latitude, location.longitude)
            if distance <= radius_km:
                nearby.append({
                    "id": str(worker.worker_id),
                    "name": user.first_name + " " + user.last_name,
                    "phone": user.phone_number,
                    "ward": worker.assigned_ward_name,
                    "availability_status": worker.availability_status.value if worker.availability_status else None,
                    "distance_km": round(distance, 2),
                    "latitude": location.latitude,
                    "longitude": location.longitude
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return {"workers": nearby, "count": len(nearby)}

    async def find_nearby_farmers(self, lat: float, lng: float, radius_km: float, crop_type: Optional[str] = None):


        query = (
            select(Farmer, Location, User)
            .join(Location, Farmer.location_id == Location.location_id)
            .join(User, Farmer.user_id == User.id)
        )
        if crop_type:
            query = query.where(Farmer.primary_crop == crop_type)

        result = await self.db.execute(query)
        rows = result.all()

        nearby = []
        for farmer, location, user in rows:
            if location.latitude is None or location.longitude is None:
                continue
            distance = self._haversine(lat, lng, location.latitude, location.longitude)
            if distance <= radius_km:
                nearby.append({
                    "id": str(farmer.farmer_id),
                    "name": user.first_name + " " + user.last_name,
                    "phone": user.phone_number,
                    "crop_type": farmer.primary_crop,
                    "ward": farmer.ward_name,
                    "distance_km": round(distance, 2),
                    "latitude": location.latitude,
                    "longitude": location.longitude
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return {"farmers": nearby, "count": len(nearby)}

    async def search_users_by_role(
        self,
        role: str,
        q: Optional[str] = None,
        ward: Optional[str] = None,
        skill: Optional[str] = None,
    ):
      

        if role in ("agritex_worker", "extension_worker"):
            query = (
                select(ExtensionWorker, User)
                .join(
                    User,
                    ExtensionWorker.user_id == User.id,
                )
            )

            if q:
                pattern = f"%{q}%"
                query = query.where(
                    or_(
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                        User.phone_number.ilike(pattern),
                    )
                )

            if ward:
                query = query.where(
                    ExtensionWorker.assigned_ward_name.ilike(
                        f"%{ward}%"
                    )
                )

            result = await self.db.execute(query)

            workers = []

            for worker, user in result.all():
                workers.append({
                    "worker_id": str(worker.worker_id),
                    "user_id": str(user.id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_number": user.phone_number,
                    "assigned_ward_name": worker.assigned_ward_name,
                    "availability_status": (
                        worker.availability_status.value
                        if worker.availability_status
                        else None
                    ),
                })

            return workers

        query = select(User).where(
            User.user_type == role
        )

        if q:
            pattern = f"%{q}%"
            query = query.where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.phone_number.ilike(pattern),
                )
            )

        result = await self.db.execute(query)

        return result.scalars().all()

