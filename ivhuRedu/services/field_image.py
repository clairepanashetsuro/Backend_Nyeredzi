from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ivhuRedu.repositories.field_image import FieldImageRepository
from ivhuRedu.schemas.field_image import ReportImageCreate, ReportImageUpdate, ReportImageResponse


class FieldImageService:

    def __init__(self, db: Session):
        self.repo = FieldImageRepository(db)

    def create_image(self, data: ReportImageCreate) -> ReportImageResponse:
        return self.repo.create(data)

    def get_images_by_report(self, report_id: UUID) -> list[ReportImageResponse]:
        return self.repo.get_by_report_id(report_id)

    def get_image(self, image_id: UUID) -> ReportImageResponse:
        img = self.repo.get_by_id(image_id)
        if not img:
            raise HTTPException(status_code=404, detail="Image not found")
        return img

    def update_image(self, image_id: UUID, data: ReportImageUpdate) -> ReportImageResponse:
        updated_img = self.repo.update(image_id, data)
        if not updated_img:
            raise HTTPException(status_code=404, detail="Image not found")
        return updated_img

    def delete_image(self, image_id: UUID) -> None:
        if not self.repo.delete(image_id):
            raise HTTPException(status_code=404, detail="Image not found")