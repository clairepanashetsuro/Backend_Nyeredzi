from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
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

@router.post("/geocode", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def geocode_location(request: LocationGeocodeRequest, db: AsyncSession = Depends(get_db)):
    service = LocationService(db)
    location = await service.geocode_and_create(request)
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    return location
