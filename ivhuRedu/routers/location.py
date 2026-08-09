from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
import os
import httpx

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
async def search_locations(q: Optional[str] = Query(None), ward: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.search(q=q, ward=ward)


@router.post("/geocode", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def geocode_location(request: LocationGeocodeRequest, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    location = await service.geocode_and_create(request)
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    return location


@router.get("/autocomplete")
async def autocomplete_address(q: str = Query(..., min_length=2)):
    api_key = os.getenv("LOCATIONIQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LOCATIONIQ_API_KEY not configured in .env")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://us1.locationiq.com/v1/autocomplete.php",
            params={"key": api_key, "q": q, "limit": 5}
        )
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return {"suggestions": data}


@router.get("/reverse")
async def reverse_geocode(lat: float = Query(...), lon: float = Query(...)):
    api_key = os.getenv("LOCATIONIQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LOCATIONIQ_API_KEY not configured in .env")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://us1.locationiq.com/v1/reverse.php",
            params={"key": api_key, "lat": lat, "lon": lon, "format": "json"}
        )
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        return data


@router.get("/workers/nearby")
async def nearby_workers(lat: float = Query(...), lng: float = Query(...), radius_km: float = Query(5.0), skill: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.find_nearby_workers(lat=lat, lng=lng, radius_km=radius_km, skill=skill)


@router.get("/farmers/nearby")
async def nearby_farmers(lat: float = Query(...), lng: float = Query(...), radius_km: float = Query(10.0), crop_type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.find_nearby_farmers(lat=lat, lng=lng, radius_km=radius_km, crop_type=crop_type)


@router.get("/farmers/search")
async def search_farmers(q: Optional[str] = Query(None), ward: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    return await service.search_users_by_role(role="farmer", q=q, ward=ward)


@router.get("/workers/search")
async def search_workers(q: Optional[str] = Query(None), ward: Optional[str] = Query(None), skill: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    users = await service.search_users_by_role(role="agritex_worker", q=q, ward=ward)
    if skill:
        users = [u for u in users if getattr(u, "skill", None) == skill]
    return users


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(location_id: UUID, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    location = await service.get_by_id(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(location_id: UUID, location_update: LocationUpdate, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    location = await service.update(location_id, location_update)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: UUID, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    success = await service.delete(location_id)
    if not success:
        raise HTTPException(status_code=404, detail="Location not found")
    return None