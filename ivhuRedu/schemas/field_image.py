
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ReportImageBase(BaseModel):
    image_url: str


class ReportImageCreate(ReportImageBase):
    report_id: UUID


class ReportImageUpdate(BaseModel):
    image_url: str | None = None


class ReportImageResponse(ReportImageBase):
    image_id: UUID
    report_id: UUID
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

