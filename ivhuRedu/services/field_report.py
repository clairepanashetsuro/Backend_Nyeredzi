from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.database import get_db
from ivhuRedu.models.field_report import StatusEnum, SyncStatus
from ivhuRedu.repositories.field_report import field_report_repository
from ivhuRedu.schemas.field_report import FieldReportCreate, FieldReportUpdate

class FieldReportService:

    @classmethod
    async def create(cls, report: FieldReportCreate, db: AsyncSession = Depends(get_db)):
        if not report.description_type or not report.description_type.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail="description_type is required."
            )
        
        report.status = StatusEnum.PENDING
        report.timestamp_synced = None

        return await field_report_repository.create(db, report)

    @classmethod
    async def get_all(cls, db: AsyncSession = Depends(get_db)):
        return await field_report_repository.get_all(db)

    @classmethod
    async def get_by_id(cls, report_id: UUID, db: AsyncSession = Depends(get_db)):
        report = await field_report_repository.get_by_id(db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Field report not found"
            )
        return report

    @classmethod
    async def get_by_worker(cls, worker_id: UUID, db: AsyncSession = Depends(get_db)):
        return await field_report_repository.get_by_worker(db, worker_id)

    @classmethod
    async def update(cls, report_id: UUID, report: FieldReportUpdate, db: AsyncSession = Depends(get_db)):
        await cls.get_by_id(report_id, db)

        if report.description_type is not None and not report.description_type.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail="Description type cannot be empty"
            )

        if report.sync_status == SyncStatus.SYNCED:
            report.timestamp_synced = datetime.now(timezone.utc)
            report.status = StatusEnum.COMPLETED
        elif report.sync_status == SyncStatus.PENDING_SYNC:
            report.timestamp_synced = None

        return await field_report_repository.update(db, report_id, report)

    @classmethod
    async def delete(cls, report_id: UUID, db: AsyncSession = Depends(get_db)):
        await cls.get_by_id(report_id, db)
        return await field_report_repository.delete(db, report_id)

field_report_service = FieldReportService()
