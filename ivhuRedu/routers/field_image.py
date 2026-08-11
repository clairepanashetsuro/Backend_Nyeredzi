from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from ivhuRedu.services.field_image import FieldImageService
from ivhuRedu.schemas.field_image import (
    ReportImageCreate,
    ReportImageResponse,
    ReportImageUpdate,
)

router = APIRouter(prefix="/field-images", tags=["Field Images"])


@router.post("/", response_model=ReportImageResponse, status_code=201)
def create_image(data: ReportImageCreate, db: Session = Depends(get_db)):
    service = FieldImageService(db)
    return service.create_image(data)


@router.get("/report/{report_id}", response_model=list[ReportImageResponse])
def get_report_images(report_id: UUID, db: Session = Depends(get_db)):
    service = FieldImageService(db)
    return service.get_images_by_report(report_id)


@router.get("/{image_id}", response_model=ReportImageResponse)
def get_image(image_id: UUID, db: Session = Depends(get_db)):
    service = FieldImageService(db)
    return service.get_image(image_id)


@router.put("/{image_id}", response_model=ReportImageResponse)
def update_image(image_id: UUID, data: ReportImageUpdate, db: Session = Depends(get_db)):
    service = FieldImageService(db)
    return service.update_image(image_id, data)


@router.delete("/{image_id}", status_code=204)
def delete_image(image_id: UUID, db: Session = Depends(get_db)):
    service = FieldImageService(db)
    service.delete_image(image_id)