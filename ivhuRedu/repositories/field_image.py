from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ivhuRedu.models.field_image import ReportImage
from ivhuRedu.schemas.field_image import ReportImageCreate, ReportImageUpdate


class FieldImageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ReportImageCreate) -> ReportImage:
       
        img = ReportImage(
            report_id=data.report_id,
            image_url=data.file_url
        )
        self.db.add(img)
        await self.db.commit()
        await self.db.refresh(img)
        return img

    async def get_by_id(self, image_id: UUID) -> ReportImage | None:
        result = await self.db.execute(
            select(ReportImage).filter(ReportImage.image_id == image_id)
        )
        return result.scalars().first()

    async def get_by_report_id(self, report_id: UUID) -> list[ReportImage]:
        result = await self.db.execute(
            select(ReportImage).filter(ReportImage.report_id == report_id)
        )
        return list(result.scalars().all())

    async def update(self, image_id: UUID, data: ReportImageUpdate) -> ReportImage | None:
        img = await self.get_by_id(image_id)
        if not img:
            return None

        
        update_data = data.model_dump(exclude_unset=True)
        if "file_url" in update_data:
            update_data["image_url"] = update_data.pop("file_url")

        for key, value in update_data.items():
            setattr(img, key, value)

        await self.db.commit()
        await self.db.refresh(img)
        return img

    async def delete(self, image_id: UUID) -> bool:
        img = await self.get_by_id(image_id)
        if not img:
            return False

        await self.db.delete(img)
        await self.db.commit()
        return True
