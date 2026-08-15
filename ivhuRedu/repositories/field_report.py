from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ivhuRedu.models.field_report import FieldReport
from ivhuRedu.schemas.field_report import FieldReportCreate, FieldReportUpdate

class FieldReportRepository:

    async def create(self, db: AsyncSession, data: FieldReportCreate):
        report_data = data.model_dump()
        report = FieldReport(**report_data)
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    async def get_all(self, db: AsyncSession):
        result = await db.execute(select(FieldReport))
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, report_id: UUID):
        result = await db.execute(
            select(FieldReport).where(FieldReport.report_id == report_id)
        )
        return result.scalar_one_or_none()

    async def get_by_worker(self, db: AsyncSession, worker_id: UUID):
        result = await db.execute(
            select(FieldReport).where(FieldReport.worker_id == worker_id)
        )
        return result.scalars().all()

    async def update(self, db: AsyncSession, report_id: UUID, data: FieldReportUpdate):
        report = await self.get_by_id(db, report_id)
        if not report:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(report, key, value)
            
        await db.commit()
        await db.refresh(report)
        return report

    async def delete(self, db: AsyncSession, report_id: UUID) -> bool:
        report = await self.get_by_id(db, report_id)
        if not report:
            return False
            
        await db.delete(report)
        await db.commit()
        return True

field_report_repository = FieldReportRepository()
