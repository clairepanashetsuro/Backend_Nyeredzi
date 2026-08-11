from uuid import UUID
from sqlalchemy.orm import Session
from ivhuRedu.models.field_image import ReportImage
from ivhuRedu.schemas.field_image import ReportImageCreate, ReportImageUpdate


class FieldImageRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: ReportImageCreate) -> ReportImage:
        img = ReportImage(**data.model_dump())
        self.db.add(img)
        self.db.commit()
        self.db.refresh(img)
        return img

    def get_by_id(self, image_id: UUID) -> ReportImage | None:
        return (
            self.db.query(ReportImage)
            .filter(ReportImage.image_id == image_id)
            .first()
        )

    def get_by_report_id(self, report_id: UUID) -> list[ReportImage]:
        return (
            self.db.query(ReportImage)
            .filter(ReportImage.report_id == report_id)
            .all()
        )

    def update(self, image_id: UUID, data: ReportImageUpdate) -> ReportImage | None:
        img = self.get_by_id(image_id)
        if not img:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(img, key, value)

        self.db.commit()
        self.db.refresh(img)
        return img

    def delete(self, image_id: UUID) -> bool:
        img = self.get_by_id(image_id)
        if not img:
            return False

        self.db.delete(img)
        self.db.commit()
        return True