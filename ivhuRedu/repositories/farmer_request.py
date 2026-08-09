import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from ivhuRedu.models.farmer_request import FarmerRequest
from ivhuRedu.schemas.farmer_request import FarmerRequestCreate, FarmerRequestUpdate

class FarmerRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj_in: FarmerRequestCreate) -> FarmerRequest:
        db_obj = FarmerRequest(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_by_id(self, request_id: uuid.UUID) -> Optional[FarmerRequest]:
        return self.db.query(FarmerRequest).filter(FarmerRequest.request_id == request_id).first()

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[FarmerRequest]:
        return self.db.query(FarmerRequest).offset(skip).limit(limit).all()

    def get_by_farmer(self, farmer_id: uuid.UUID) -> List[FarmerRequest]:
        return self.db.query(FarmerRequest).filter(FarmerRequest.farmer_id == farmer_id).all()

    def update(self, db_obj: FarmerRequest, obj_in: FarmerRequestUpdate) -> FarmerRequest:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, db_obj: FarmerRequest) -> None:
        self.db.delete(db_obj)
        self.db.commit()
