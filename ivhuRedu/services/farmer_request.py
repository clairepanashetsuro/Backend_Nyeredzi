import enum
import math
import uuid
from datetime import datetime
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ivhuRedu.schemas.farmer_request import FarmerRequestCreate, FarmerRequestUpdate
from ivhuRedu.models.farmer_request import FarmerRequest

try:
    from ivhuRedu.services.location import LocationService
except ImportError:
    LocationService = None


class FarmerRequestService:
    def __init__(self, db: Session):
        self.db = db

    def _get_users_model(self):
        try:
            from ivhuRedu.models.user import User
            return User
        except ImportError:
            try:
                from ivhuRedu.models.user import users
                return users
            except ImportError:
                try:
                    from ivhuRedu.models.user import Users
                    return Users
                except ImportError:
                    return None

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _calculate_distance(self, farmer_lat: float, farmer_lng: float, worker_lat: float, worker_lng: float) -> float:
        if LocationService is not None:
            return LocationService._haversine(farmer_lat, farmer_lng, worker_lat, worker_lng)
        return self._haversine(farmer_lat, farmer_lng, worker_lat, worker_lng)

    def _set_distance_for_request(self, request: FarmerRequest):
        if not request.farmer_id or not request.worker_id:
            return

        User = self._get_users_model()
        if not User:
            return

        farmer = self.db.query(User).filter(User.id == request.farmer_id).first()
        worker = self.db.query(User).filter(User.id == request.worker_id).first()

        if (farmer and worker and
            getattr(farmer, "latitude", None) is not None and
            getattr(farmer, "longitude", None) is not None and
            getattr(worker, "latitude", None) is not None and
            getattr(worker, "longitude", None) is not None):

            distance_km = self._calculate_distance(
                farmer.latitude, farmer.longitude,
                worker.latitude, worker.longitude
            )
            request.distance_m = round(distance_km * 1000, 2)
            self.db.commit()
            self.db.refresh(request)

    def create_farmer_request(self, request_in: FarmerRequestCreate):
        db_obj = FarmerRequest(
            request_id=uuid.uuid4(),
            request_type=request_in.request_type.value,
            ussd_input_text=request_in.ussd_input_text,
            sync_status=request_in.sync_status or "pending_sync",
            farmer_id=request_in.farmer_id,
            worker_id=request_in.worker_id,
            request_status="pending",
            created_at=datetime.utcnow(),
            resolved_at=None
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        if db_obj.worker_id:
            self._set_distance_for_request(db_obj)

        return db_obj

    def create_multiple_farmer_requests(self, requests_in: List[FarmerRequestCreate]):
        created_records = []
        for req in requests_in:
            db_obj = FarmerRequest(
                request_id=uuid.uuid4(),
                request_type=req.request_type.value,
                ussd_input_text=req.ussd_input_text,
                sync_status=req.sync_status or "pending_sync",
                farmer_id=req.farmer_id,
                worker_id=req.worker_id,
                request_status="pending",
                created_at=datetime.utcnow(),
                resolved_at=None
            )
            self.db.add(db_obj)
            created_records.append(db_obj)

        self.db.commit()
        for record in created_records:
            self.db.refresh(record)
            if record.worker_id:
                self._set_distance_for_request(record)
        return created_records

    def remove_duplicate_requests(self) -> int:
        all_records = self.db.query(FarmerRequest).order_by(FarmerRequest.created_at.asc()).all()
        to_delete_ids = []
        seen = set()

        for r in all_records:
            fingerprint = (r.farmer_id, r.request_type)
            if fingerprint in seen:
                to_delete_ids.append(r.request_id)
            else:
                seen.add(fingerprint)

        if to_delete_ids:
            self.db.query(FarmerRequest).filter(
                FarmerRequest.request_id.in_(to_delete_ids)
            ).delete(synchronize_session=False)
            self.db.commit()

        return len(to_delete_ids)

    def search_requests_by_ussd_keyword(self, keyword: str) -> List[FarmerRequest]:
        search_filter = f"%{keyword}%"
        return self.db.query(FarmerRequest).filter(
            FarmerRequest.request_type.ilike(search_filter)
        ).all()

    def assign_requests_to_worker_batch(self, request_ids: List[uuid.UUID], worker_id: uuid.UUID) -> List[FarmerRequest]:
        self.db.query(FarmerRequest).filter(
            FarmerRequest.request_id.in_(request_ids)
        ).update(
            {
                FarmerRequest.worker_id: worker_id,
                FarmerRequest.request_status: "assigned"
            },
            synchronize_session=False
        )
        self.db.commit()

        for req_id in request_ids:
            req = self.db.query(FarmerRequest).filter(
                FarmerRequest.request_id == req_id
            ).first()
            if req:
                self._set_distance_for_request(req)

        return self.db.query(FarmerRequest).filter(
            FarmerRequest.request_id.in_(request_ids)
        ).all()

    def get_farmer_request_by_id(self, request_id: uuid.UUID):
        records = self.db.query(FarmerRequest).filter(
            FarmerRequest.request_id == request_id
        ).all()
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farmer request with ID {request_id} not found"
            )
        return records[0]

    def get_all_farmer_requests(self, skip: int = 0, limit: int = 100):
        return self.db.query(FarmerRequest).offset(skip).limit(limit).all()

    def get_requests_by_specific_farmer(self, farmer_id: uuid.UUID):
        return self.db.query(FarmerRequest).filter(
            FarmerRequest.farmer_id == farmer_id
        ).all()

    def update_farmer_request_details(self, request_id: uuid.UUID, request_in: FarmerRequestUpdate):
        records = self.db.query(FarmerRequest).filter(
            FarmerRequest.request_id == request_id
        ).all()

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farmer request with ID {request_id} not found"
            )

        record = records[0]
        update_data = request_in.model_dump(exclude_unset=True)

        for key in ("request_type", "request_status"):
            if key in update_data and isinstance(update_data[key], enum.Enum):
                update_data[key] = update_data[key].value

        if update_data.get("request_status") == "resolved" and not record.resolved_at:
            record.resolved_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(record, field, value)

        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_farmer_request_record(self, request_id: uuid.UUID):
        records = self.db.query(FarmerRequest).filter(
            FarmerRequest.request_id == request_id
        ).all()
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farmer request with ID {request_id} not found"
            )

        self.db.delete(records[0])
        self.db.commit()
        return None
