import uuid
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ivhuRedu.models.farmer_request import FarmerRequest


class FarmerRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, request_data: dict) -> FarmerRequest:
        db_request = FarmerRequest(**request_data)
        self.db.add(db_request)
        self.db.commit()
        self.db.refresh(db_request)
        return db_request

    def create_multiple(self, requests_data: List[dict]) -> List[FarmerRequest]:
        created = []
        for data in requests_data:
            db_request = FarmerRequest(**data)
            self.db.add(db_request)
            created.append(db_request)
        self.db.commit()
        for req in created:
            self.db.refresh(req)
        return created

    def get_by_phone(self, phone_number: str) -> List[FarmerRequest]:
        return self.db.query(FarmerRequest).filter(
            FarmerRequest.phone_number == phone_number
        ).order_by(FarmerRequest.created_at.desc()).all()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[FarmerRequest]:
        return self.db.query(FarmerRequest).offset(skip).limit(limit).all()

    def get_by_farmer_id(self, farmer_id: uuid.UUID) -> List[FarmerRequest]:
        return self.db.query(FarmerRequest).filter(
            FarmerRequest.farmer_id == farmer_id
        ).order_by(FarmerRequest.created_at.desc()).all()

    def get_by_id(self, request_id: uuid.UUID) -> Optional[FarmerRequest]:
        return self.db.query(FarmerRequest).filter(
            FarmerRequest.request_id == request_id
        ).first()

    def update(self, db_request: FarmerRequest, update_data: dict) -> FarmerRequest:
        for field, value in update_data.items():
            setattr(db_request, field, value)
        self.db.commit()
        self.db.refresh(db_request)
        return db_request

    def delete(self, db_request: FarmerRequest) -> None:
        self.db.delete(db_request)
        self.db.commit()

    def search_by_keyword(self, keyword: str) -> List[FarmerRequest]:
        search = f"%{keyword}%"
        return self.db.query(FarmerRequest).filter(
            or_(
                FarmerRequest.request_type.ilike(search),
                FarmerRequest.status.ilike(search),
                FarmerRequest.phone_number.ilike(search),
                FarmerRequest.description.ilike(search),
                FarmerRequest.location.ilike(search)
            )
        ).order_by(FarmerRequest.created_at.desc()).all()

    def assign_to_worker(self, request_ids: List[uuid.UUID], worker_id: uuid.UUID) -> List[FarmerRequest]:
        requests = self.db.query(FarmerRequest).filter(
            FarmerRequest.request_id.in_(request_ids)
        ).all()

        for req in requests:
            req.assigned_worker_id = worker_id
            req.status = "assigned"

        self.db.commit()
        for req in requests:
            self.db.refresh(req)
        return requests

    def remove_duplicates(self) -> int:
        subquery = self.db.query(
            FarmerRequest.phone_number,
            FarmerRequest.request_type,
            FarmerRequest.status,
            func.min(FarmerRequest.created_at).label("min_created")
        ).group_by(
            FarmerRequest.phone_number,
            FarmerRequest.request_type,
            FarmerRequest.status
        ).having(func.count(FarmerRequest.request_id) > 1).subquery()

        duplicates = self.db.query(FarmerRequest).join(
            subquery,
            (FarmerRequest.phone_number == subquery.c.phone_number) &
            (FarmerRequest.request_type == subquery.c.request_type) &
            (FarmerRequest.status == subquery.c.status) &
            (FarmerRequest.created_at > subquery.c.min_created)
        ).all()

        count = len(duplicates)
        for dup in duplicates:
            self.db.delete(dup)

        self.db.commit()
        return count