from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.database import get_db
from ivhuRedu.repositories.field_report import field_report_repository

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
    return await field_report_repository.create(db, report)


@router.get("/", response_model=list[FieldReportResponse])
async def get_field_reports(
    db: AsyncSession = Depends(get_db),
):
    return await field_report_repository.get_all(db)


@router.get("/{report_id}", response_model=FieldReportResponse)
async def get_field_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    report = await field_report_repository.get_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field report not found",
        )
    return report


@router.patch("/{report_id}", response_model=FieldReportResponse)
async def update_field_report(
    report_id: UUID,
    report: FieldReportUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated_report = await field_report_repository.update(db, report_id, report)
    if not updated_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field report not found",
        )
    return updated_report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    deleted = await field_report_repository.delete(db, report_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field report not found",
        )
    return None
