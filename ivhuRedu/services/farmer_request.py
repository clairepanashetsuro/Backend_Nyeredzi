import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from ivhuRedu.repositories.farmer_request import FarmerRequestRepository
from ivhuRedu.schemas.farmer_request import FarmerRequestCreate, FarmerRequestUpdate


class FarmerRequestService:
    def __init__(self, db: Session):
        self.repo = FarmerRequestRepository(db)

    def create_farmer_request(self, request_in: FarmerRequestCreate):
        request_data = {
            "phone_number": request_in.phone_number,
            "request_type": request_in.request_type,
            "ussd_session_id": request_in.ussd_session_id,
            "status": request_in.status or "pending",
            "description": request_in.description,
            "location": request_in.location,
            "farmer_id": request_in.farmer_id
        }
        return self.repo.create(request_data)

    def create_multiple_farmer_requests(self, requests_in: List[FarmerRequestCreate]):
        requests_data = []
        for req_in in requests_in:
            requests_data.append({
                "phone_number": req_in.phone_number,
                "request_type": req_in.request_type,
                "ussd_session_id": req_in.ussd_session_id,
                "status": req_in.status or "pending",
                "description": req_in.description,
                "location": req_in.location,
                "farmer_id": req_in.farmer_id
            })
        return self.repo.create_multiple(requests_data)
        

    def get_requests_by_phone(self, phone_number: str):
        return self.repo.get_by_phone(phone_number)

    def get_all_farmer_requests(self, skip: int = 0, limit: int = 100):
        return self.repo.get_all(skip, limit)

    def get_requests_by_specific_farmer(self, farmer_id: uuid.UUID):
        return self.repo.get_by_farmer_id(farmer_id)

    def get_farmer_request_by_id(self, request_id: uuid.UUID):
        return self.repo.get_by_id(request_id)

    def update_farmer_request_details(self, request_id: uuid.UUID, request_in: FarmerRequestUpdate):
        db_request = self.repo.get_by_id(request_id)
        if not db_request:
            raise ValueError("Request not found")

        update_data = request_in.model_dump(exclude_unset=True)
        return self.repo.update(db_request, update_data)

    def delete_farmer_request_record(self, request_id: uuid.UUID):
        db_request = self.repo.get_by_id(request_id)
        if not db_request:
            raise ValueError("Request not found")
        self.repo.delete(db_request)

    def search_requests_by_ussd_keyword(self, keyword: str):
        return self.repo.search_by_keyword(keyword)

    def assign_requests_to_worker_batch(self, request_ids: List[uuid.UUID], worker_id: uuid.UUID):
        return self.repo.assign_to_worker(request_ids, worker_id)

    def remove_duplicate_requests(self):
        return self.repo.remove_duplicates()