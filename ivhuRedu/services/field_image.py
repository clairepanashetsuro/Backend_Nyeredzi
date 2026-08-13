from uuid import UUID
from fastapi import HTTPException, status  
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.repositories.field_image import FieldImageRepository
from ivhuRedu.schemas.field_image import ReportImageCreate, ReportImageUpdate, ReportImageResponse


class FieldImageService:

    def __init__(self, db: AsyncSession):
        self.repo = FieldImageRepository(db)

    async def create_image(self, data: ReportImageCreate) -> ReportImageResponse:
        return await self.repo.create(data)

    async def get_images_by_report(self, report_id: UUID) -> list[ReportImageResponse]:
        return await self.repo.get_by_report_id(report_id)

    async def get_image(self, image_id: UUID) -> ReportImageResponse:
        img = await self.repo.get_by_id(image_id)
        if not img:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Image not found"
            )
        return img

    async def update_image(self, image_id: UUID, data: ReportImageUpdate) -> ReportImageResponse:
        updated_img = await self.repo.update(image_id, data)
        if not updated_img:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Image not found"
            )
        return updated_img

    async def delete_image(self, image_id: UUID) -> None:
        if not await self.repo.delete(image_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Image not found"
            )
