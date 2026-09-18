from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.field_report import StatusEnum, SyncStatus
from ivhuRedu.repositories.field_report import FieldReportRepository
from ivhuRedu.schemas.field_report import (
    FieldReportCreate,
    FieldReportUpdate,
)


class FieldReportService:

    def __init__(self, db: AsyncSession):
        self.repo = FieldReportRepository(db)

    async def create(
        self,
        data: FieldReportCreate,
        current_user,
    ):

        if (
            not data.description_type
            or not data.description_type.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="description_type is required.",
            )

        if current_user.user_type.value == "extension_worker":
            if current_user.extension_worker is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Extension Worker profile not found.",
                )

            data.worker_id = current_user.extension_worker.worker_id

        data.status = StatusEnum.PENDING
        data.timestamp_synced = None

        return await self.repo.create(data)

    async def get_all(self, current_user):

        if current_user.user_type.value == "admin":
            return await self.repo.get_all()

        if current_user.user_type.value != "extension_worker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access field reports.",
            )

        if current_user.extension_worker is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Extension Worker profile not found.",
            )

        return await self.repo.get_by_worker(
            current_user.extension_worker.worker_id
        )

    async def get_by_id(
        self,
        report_id: UUID,
        current_user,
    ):
        report = await self.repo.get_by_id(report_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Field report not found",
            )

        if current_user.user_type.value == "admin":
            return report

        if current_user.user_type.value != "extension_worker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this report",
            )

        if current_user.extension_worker is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Extension Worker profile not found.",
            )

        if (
            report.worker_id
            != current_user.extension_worker.worker_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this report",
            )

        return report

    async def get_by_worker(
        self,
        worker_id: UUID,
        current_user,
    ):
        if current_user.user_type.value == "admin":
            return await self.repo.get_by_worker(worker_id)

        if current_user.user_type.value != "extension_worker":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access these reports",
            )

        if current_user.extension_worker is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Extension Worker profile not found.",
            )

        if (
            worker_id
            != current_user.extension_worker.worker_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access these reports",
            )

        return await self.repo.get_by_worker(worker_id)

    async def update(
        self,
        report_id: UUID,
        data: FieldReportUpdate,
        current_user,
    ):
        report = await self.get_by_id(
            report_id,
            current_user,
        )

        if (
            data.description_type is not None
            and not data.description_type.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Description type cannot be empty",
            )

        if (
            current_user.user_type.value == "extension_worker"
            and current_user.extension_worker is not None
        ):
            data.worker_id = current_user.extension_worker.worker_id

        if data.sync_status == SyncStatus.SYNCED:
            data.timestamp_synced = datetime.now(timezone.utc)
            data.status = StatusEnum.COMPLETED

        elif data.sync_status == SyncStatus.PENDING_SYNC:
            data.timestamp_synced = None

        return await self.repo.update(
            report_id,
            data,
        )

    async def delete(
        self,
        report_id: UUID,
        current_user,
    ):
        await self.get_by_id(
            report_id,
            current_user,
        )

        deleted = await self.repo.delete(
            report_id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Field report not found",
            )