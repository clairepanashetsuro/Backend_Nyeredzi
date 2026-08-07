import math
import os
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from uuid import UUID

from ivhuRedu.models.location import Location
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
        result = await self.db.execute(select(Location).where(Location.id == location_id))
        return result.scalar_one_or_none()

    async def update(self, location_id: UUID, location_update: LocationUpdate):
        location = await self.get_by_id(location_id)
        if not location:
            return None
        for field, value in location_update.dict(exclude_unset=True).items():
            setattr(location, field, value)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def delete(self, location_id: UUID):
        location = await self.get_by_id(location_id)
        if not location:
            return False
        await self.db.delete(location)
        await self.db.commit()
        return True

    async def search(self, q: Optional[str] = None, ward: Optional[str] = None):
        query = select(Location)
        if q:
            query = query.where(or_(Location.name.ilike(f"%{q}%"), Location.ward.ilike(f"%{q}%")))
        if ward:
            query = query.where(Location.ward.ilike(f"%{ward}%"))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def geocode_and_create(self, request: LocationGeocodeRequest):
        api_key = os.getenv("LOCATIONIQ_API_KEY")
        if not api_key:
            raise Exception("LOCATIONIQ_API_KEY not configured in .env")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://us1.locationiq.com/v1/search.php",
                params={"key": api_key, "q": request.address, "format": "json", "limit": 1}
            )
            data = response.json()

        if isinstance(data, dict) and "error" in data:
            raise Exception(f"LocationIQ error: {data.get('error')}")
        if not data:
            return None

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])

        location_data = LocationCreate(
            name=getattr(request, "name", None) or request.address,
            address=request.address,
            latitude=lat,
            longitude=lon,
            ward=getattr(request, "ward", None)
        )

        return await self.create(location_data)

    def _get_users_model(self):
        try:
            from ivhuRedu.models.users import users
            return users
        except ImportError:
            try:
                from ivhuRedu.models.users import User as users
                return users
            except ImportError:
                try:
                    from ivhuRedu.models.users import Users as users
                    return users
                except ImportError:
                    return None

    async def find_nearby_workers(self, lat: float, lng: float, radius_km: float, skill: Optional[str] = None):
        users = self._get_users_model()
        if not users:
            return {"workers": [], "count": 0, "note": "users.py model not found - teammate has not merged yet"}

        query = select(users).where(
            users.role == "agritex_worker",
            users.latitude.isnot(None),
            users.longitude.isnot(None)
        )
        if skill and hasattr(users, "skill"):
            query = query.where(users.skill == skill)

        result = await self.db.execute(query)
        workers = result.scalars().all()

        nearby = []
        for worker in workers:
            distance = self._haversine(lat, lng, worker.latitude, worker.longitude)
            if distance <= radius_km:
                nearby.append({
                    "id": str(worker.id),
                    "name": getattr(worker, "name", None),
                    "phone": getattr(worker, "phone", None),
                    "skill": getattr(worker, "skill", None),
                    "ward": getattr(worker, "ward", None),
                    "distance_km": round(distance, 2),
                    "latitude": worker.latitude,
                    "longitude": worker.longitude
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return {"workers": nearby, "count": len(nearby)}

    async def find_nearby_farmers(self, lat: float, lng: float, radius_km: float, crop_type: Optional[str] = None):
        users = self._get_users_model()
        if not users:
            return {"farmers": [], "count": 0, "note": "users.py model not found - teammate has not merged yet"}

        query = select(users).where(
            users.role == "farmer",
            users.latitude.isnot(None),
            users.longitude.isnot(None)
        )
        if crop_type and hasattr(users, "crop_type"):
            query = query.where(users.crop_type == crop_type)

        result = await self.db.execute(query)
        farmers = result.scalars().all()

        nearby = []
        for farmer in farmers:
            distance = self._haversine(lat, lng, farmer.latitude, farmer.longitude)
            if distance <= radius_km:
                nearby.append({
                    "id": str(farmer.id),
                    "name": getattr(farmer, "name", None),
                    "phone": getattr(farmer, "phone", None),
                    "crop_type": getattr(farmer, "crop_type", None),
                    "ward": getattr(farmer, "ward", None),
                    "distance_km": round(distance, 2),
                    "latitude": farmer.latitude,
                    "longitude": farmer.longitude
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return {"farmers": nearby, "count": len(nearby)}

    async def search_users_by_role(self, role: str, q: Optional[str] = None, ward: Optional[str] = None):
        users = self._get_users_model()
        if not users:
            return []

        query = select(users).where(users.role == role)
        if q and hasattr(users, "name"):
            query = query.where(users.name.ilike(f"%{q}%"))
        if ward and hasattr(users, "ward"):
            query = query.where(users.ward.ilike(f"%{ward}%"))
        result = await self.db.execute(query)
        return result.scalars().all()