from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional
from datetime import datetime
from ivhuRedu.models.field_report import StatusEnum, IssueType, SyncStatus

class FieldReportCreate(BaseModel):
    worker_id: UUID
    farmer_id: Optional[UUID] = None
    related_request_id: Optional[UUID] = None
    issue_type: Optional[IssueType] = None
    report_details: Optional[str] = None
    details: Optional[str] = None
    description_type: str
    ussd_description: Optional[str] = None
    ussd_info: Optional[str] = None
    sync_status: Optional[SyncStatus] = SyncStatus.PENDING_SYNC
    status: Optional[StatusEnum] = StatusEnum.PENDING
    timestamp_synced: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FieldReportUpdate(BaseModel):
    worker_id: Optional[UUID] = None
    farmer_id: Optional[UUID] = None
    related_request_id: Optional[UUID] = None
    issue_type: Optional[IssueType] = None
    report_details: Optional[str] = None
    details: Optional[str] = None
    description_type: Optional[str] = None
    ussd_description: Optional[str] = None
    ussd_info: Optional[str] = None
    sync_status: Optional[SyncStatus] = None
    status: Optional[StatusEnum] = None
    timestamp_synced: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FieldReportResponse(BaseModel):
    report_id: UUID
    worker_id: UUID
    farmer_id: Optional[UUID]
    related_request_id: Optional[UUID]
    issue_type: Optional[IssueType]
    report_details: Optional[str]
    details: Optional[str]
    description_type: str
    ussd_description: Optional[str]
    ussd_info: Optional[str]
    sync_status: SyncStatus
    status: StatusEnum
    timestamp_captured: datetime
    timestamp_synced: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
