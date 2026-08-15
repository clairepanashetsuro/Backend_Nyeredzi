from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.field_report import StatusEnum, SyncStatus
from ivhuRedu.repositories.field_report import field_report_repository
from ivhuRedu.schemas.field_report import FieldReportCreate, FieldReportUpdate

class FieldReportService:

    async def create(self, db: AsyncSession, data: FieldReportCreate):
        if not data.description_type or not data.description_type.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail="description_type is required."
            )
        
        data.status = StatusEnum.PENDING
        data.timestamp_synced = None

        return await field_report_repository.create(db, data)

    async def get_all(self, db: AsyncSession):
        return await field_report_repository.get_all(db)

    async def get_by_id(self, db: AsyncSession, report_id: UUID):
        report = await field_report_repository.get_by_id(db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Field report not found"
            )
        return report

    async def get_by_worker(self, db: AsyncSession, worker_id: UUID):
        return await field_report_repository.get_by_worker(db, worker_id)

    async def update(self, db: AsyncSession, report_id: UUID, data: FieldReportUpdate):
        await self.get_by_id(db, report_id)

        if data.description_type is not None and not data.description_type.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail="Description type cannot be empty"
            )

        if data.sync_status == SyncStatus.SYNCED:
            data.timestamp_synced = datetime.now(timezone.utc)
            data.status = StatusEnum.COMPLETED
        elif data.sync_status == SyncStatus.PENDING_SYNC:
            data.timestamp_synced = None

        return await field_report_repository.update(db, report_id, data)

    async def delete(self, db: AsyncSession, report_id: UUID):
        await self.get_by_id(db, report_id)
        return await field_report_repository.delete(db, report_id)

field_report_service = FieldReportService()
