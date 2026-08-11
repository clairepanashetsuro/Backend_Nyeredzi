import uuid
from typing import List

from fastapi import APIRouter, Depends, status, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import get_db
from ivhuRedu.services.farmer_request import FarmerRequestService
from ivhuRedu.services.ussd import USSDService
from ivhuRedu.schemas.farmer_request import FarmerRequestCreate, FarmerRequestUpdate

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_farmer_request(request_in: FarmerRequestCreate, db: Session = Depends(get_db)):
    return FarmerRequestService(db).create_farmer_request(request_in)


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def create_multiple_farmer_requests(requests_in: List[FarmerRequestCreate], db: Session = Depends(get_db)):
    return FarmerRequestService(db).create_multiple_farmer_requests(requests_in)


@router.post("/duplicates/cleanup", status_code=status.HTTP_200_OK)
def remove_duplicate_requests(db: Session = Depends(get_db)):
    removed_count = FarmerRequestService(db).remove_duplicate_requests()
    return {"message": f"Successfully removed {removed_count} duplicate farmer requests."}


@router.get("/search")
def search_requests_by_ussd_keyword(keyword: str, db: Session = Depends(get_db)):
    return FarmerRequestService(db).search_requests_by_ussd_keyword(keyword)


@router.post("/assign")
def assign_requests_to_worker_batch(
    request_ids: List[uuid.UUID],
    worker_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    return FarmerRequestService(db).assign_requests_to_worker_batch(request_ids, worker_id)


@router.get("/")
def get_all_farmer_requests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return FarmerRequestService(db).get_all_farmer_requests(skip, limit)


@router.get("/farmer/{farmer_id}")
def get_farmer_requests_by_farmer_id(farmer_id: uuid.UUID, db: Session = Depends(get_db)):
    return FarmerRequestService(db).get_requests_by_specific_farmer(farmer_id)


@router.get("/{request_id}")
def get_farmer_request_by_request_id(request_id: uuid.UUID, db: Session = Depends(get_db)):
    return FarmerRequestService(db).get_farmer_request_by_id(request_id)


@router.patch("/{request_id}")
def update_farmer_request(
    request_id: uuid.UUID,
    request_in: FarmerRequestUpdate,
    db: Session = Depends(get_db)
):
    service = FarmerRequestService(db)
    return service.update_farmer_request_details(request_id, request_in)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farmer_request_record(request_id: uuid.UUID, db: Session = Depends(get_db)):
    FarmerRequestService(db).delete_farmer_request_record(request_id)