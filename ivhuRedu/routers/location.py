from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from database import get_db
from ivhuRedu.schemas.location import LocationCreate, LocationResponse, LocationUpdate, LocationGeocodeRequest
from ivhuRedu.services.location import LocationService

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(location: LocationCreate, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.create(location)


@router.get("/", response_model=List[LocationResponse])
async def list_locations(db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.get_all()


@router.get("/search", response_model=List[LocationResponse])
async def search_locations(q: Optional[str] = None, ward: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.search(q=q, ward=ward)


@router.post("/geocode", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def geocode_location(request: LocationGeocodeRequest, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.geocode_and_create(request)


@router.get("/autocomplete")
async def autocomplete_address(q: str, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.autocomplete_address(q)


@router.get("/reverse")
async def reverse_geocode(lat: float, lon: float, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.reverse_geocode(lat, lon)


@router.get("/workers/nearby")
async def nearby_workers(lat: float, lng: float, radius_km: float = 5.0, skill: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.find_nearby_workers(lat=lat, lng=lng, radius_km=radius_km, skill=skill)


@router.get("/farmers/nearby")
async def nearby_farmers(lat: float, lng: float, radius_km: float = 10.0, crop_type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.find_nearby_farmers(lat=lat, lng=lng, radius_km=radius_km, crop_type=crop_type)


@router.get("/farmers/search")
async def search_farmers(q: Optional[str] = None, ward: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.search_users_by_role(role="farmer", q=q, ward=ward)


@router.get("/workers/search")
async def search_workers(q: Optional[str] = None, ward: Optional[str] = None, skill: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.search_users_by_role(role="agritex_worker", q=q, ward=ward, skill=skill)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(location_id: UUID, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.get_by_id(location_id)


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(location_id: UUID, location_update: LocationUpdate, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.update(location_id, location_update)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: UUID, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.delete(location_id)