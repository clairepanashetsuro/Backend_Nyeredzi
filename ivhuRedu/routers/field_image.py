from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from ivhuRedu.services.field_image import FieldImageService
from ivhuRedu.schemas.field_image import (
    ReportImageCreate,
    ReportImageResponse,
    ReportImageUpdate,
)

router = APIRouter(prefix="/field-images", tags=["Field Images"])


@router.post("/", response_model=ReportImageResponse, status_code=status.HTTP_201_CREATED)
async def create_image(data: ReportImageCreate, db: AsyncSession = Depends(get_db)):
    service = FieldImageService(db)
    return await service.create_image(data)


@router.get("/report/{report_id}", response_model=list[ReportImageResponse])
async def get_report_images(report_id: UUID, db: AsyncSession = Depends(get_db)):
    service = FieldImageService(db)
    return await service.get_images_by_report(report_id)


@router.get("/{image_id}", response_model=ReportImageResponse)
async def get_image(image_id: UUID, db: AsyncSession = Depends(get_db)):
    service = FieldImageService(db)
    return await service.get_image(image_id)


@router.put("/{image_id}", response_model=ReportImageResponse)
async def update_image(image_id: UUID, data: ReportImageUpdate, db: AsyncSession = Depends(get_db)):
    service = FieldImageService(db)
    return await service.update_image(image_id, data)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: UUID, db: AsyncSession = Depends(get_db)):
    service = FieldImageService(db)
    await service.delete_image(image_id)
