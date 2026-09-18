
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ivhuRedu.models.field_report import FieldReport
from ivhuRedu.schemas.field_report import (
    FieldReportCreate,
    FieldReportUpdate,
)


class FieldReportRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: FieldReportCreate):
        report = FieldReport(**data.model_dump())
        self.db.add(report)

        await self.db.commit()

        result = await self.db.execute(
            select(FieldReport)
            .options(
                selectinload(FieldReport.images)
            )
            .where(
                FieldReport.report_id == report.report_id
            )
        )

        return result.scalar_one()

    async def get_all(self):
        result = await self.db.execute(
            select(FieldReport).options(
                selectinload(FieldReport.images)
            )
        )
        return result.scalars().all()

    async def get_by_id(self, report_id: UUID):
        result = await self.db.execute(
            select(FieldReport)
            .options(
                selectinload(FieldReport.images)
            )
            .where(
                FieldReport.report_id == report_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_worker(self, worker_id: UUID):
        result = await self.db.execute(
            select(FieldReport)
            .options(
                selectinload(FieldReport.images)
            )
            .where(
                FieldReport.worker_id == worker_id
            )
        )
        return result.scalars().all()

    async def update(
        self,
        report_id: UUID,
        data: FieldReportUpdate,
    ):
        report = await self.get_by_id(report_id)

        if not report:
            return None

        update_data = data.model_dump(
            exclude_unset=True
        )

        for key, value in update_data.items():
            setattr(report, key, value)

        await self.db.commit()

        result = await self.db.execute(
            select(FieldReport)
            .options(
                selectinload(FieldReport.images)
            )
            .where(
                FieldReport.report_id == report_id
            )
        )

        return result.scalar_one()

    async def delete(self, report_id: UUID) -> bool:
        report = await self.get_by_id(report_id)

        if not report:
            return False

        await self.db.delete(report)
        await self.db.commit()

        return True


field_report_repository = FieldReportRepository

