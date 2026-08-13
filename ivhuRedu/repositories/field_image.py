from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ivhuRedu.models.field_image import ReportImage
from ivhuRedu.schemas.field_image import ReportImageCreate, ReportImageUpdate


class FieldImageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ReportImageCreate) -> ReportImage:
        img = ReportImage(**data.model_dump())
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

        for key, value in data.model_dump(exclude_unset=True).items():
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
