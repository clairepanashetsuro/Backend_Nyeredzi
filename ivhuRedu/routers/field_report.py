from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.database import get_db
from ivhuRedu.services.security import get_current_user
from ivhuRedu.models.user import User
from ivhuRedu.services.field_report import FieldReportService
from ivhuRedu.schemas.field_report import (
    FieldReportCreate,
    FieldReportUpdate,
    FieldReportResponse,
)

router = APIRouter(
    prefix="/field-reports",
    tags=["Field Reports"],
)


@router.post("/", response_model=FieldReportResponse, status_code=status.HTTP_201_CREATED)
async def create_field_report(
    report: FieldReportCreate,
    db: AsyncSession = Depends(get_db),
):
    service = FieldReportService(db)
    return await service.create(report)


@router.get("/", response_model=list[FieldReportResponse])
async def get_field_reports(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = FieldReportService(db)
    return await service.get_all(current_user)


@router.get("/{report_id}", response_model=FieldReportResponse)
async def get_field_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = FieldReportService(db)
    return await service.get_by_id(report_id, current_user)


@router.get("/worker/{worker_id}", response_model=list[FieldReportResponse])
async def get_field_reports_by_worker(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = FieldReportService(db)
    return await service.get_by_worker(worker_id, current_user)


@router.patch("/{report_id}", response_model=FieldReportResponse)
async def update_field_report(
    report_id: UUID,
    report: FieldReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = FieldReportService(db)
    return await service.update(report_id, report, current_user)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = FieldReportService(db)
    await service.delete(report_id, current_user)
    return None
