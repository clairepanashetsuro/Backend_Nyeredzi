from uuid import UUID
from fastapi import APIRouter, Depends, status

from ivhuRedu.services.field_report import field_report_service  
from ivhuRedu.schemas.field_report import (
    FieldReportResponse,
)

router = APIRouter(
    prefix="/field-reports",
    tags=["Field Reports"],
)


@router.post("/", response_model=FieldReportResponse, status_code=status.HTTP_201_CREATED)
async def create_field_report(
    report: FieldReportResponse = Depends(field_report_service.create),
):
    return report


@router.get("/", response_model=list[FieldReportResponse])
async def get_field_reports(
    reports: list[FieldReportResponse] = Depends(field_report_service.get_all),
):
    return reports


@router.get("/{report_id}", response_model=FieldReportResponse)
async def get_field_report(
    report: FieldReportResponse = Depends(field_report_service.get_by_id),
):
    return report


@router.get("/worker/{worker_id}", response_model=list[FieldReportResponse])
async def get_field_reports_by_worker(
    reports: list[FieldReportResponse] = Depends(field_report_service.get_by_worker),
):
    return reports


@router.patch("/{report_id}", response_model=FieldReportResponse)
async def update_field_report(
    updated_report: FieldReportResponse = Depends(field_report_service.update),
):
    return updated_report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_report(
    _ = Depends(field_report_service.delete),
):
    return None
