import uuid
from typing import List

from fastapi import APIRouter, Depends, status, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import get_db
from ivhuRedu.services.farmer_request import FarmerRequestService
from ivhuRedu.schemas.farmer_request import FarmerRequestCreate, FarmerRequestUpdate

router = APIRouter()


@router.post("/ussd/callback", response_class=PlainTextResponse)
def ussd_callback(
    session_id: str = Form(...),
    phone_number: str = Form(...),
    text: str = Form(default=""),
    service_code: str = Form(default=""),
    db: Session = Depends(get_db)
):
    inputs = text.split("*") if text else []
    level = len(inputs)

    if level == 0 or text == "":
        return (
            "CON Welcome to IvhuRedu\n"
            "1. Submit Request\n"
            "2. Check My Requests"
        )

    if level == 1:
        if inputs[0] == "1":
            return (
                "CON Select request type:\n"
                "1. Soil Testing\n"
                "2. Seed Supply\n"
                "3. Extension Visit\n"
                "4. Fertilizer Request"
            )
        elif inputs[0] == "2":
            requests = FarmerRequestService(db).get_requests_by_phone(phone_number)
            if not requests:
                return "END You have no active requests."
            
            response = "CON Your Requests:\n"
            for idx, req in enumerate(requests[:5], 1):
                response += f"{idx}. {req.request_type} - {req.status}\n"
            response += "0. Back"
            return response
        else:
            return "END Invalid selection."

    if level == 2:
        if inputs[0] == "1":
            request_types = {
                "1": "Soil Testing",
                "2": "Seed Supply",
                "3": "Extension Visit",
                "4": "Fertilizer Request"
            }
            selected_type = request_types.get(inputs[1])
            if not selected_type:
                return "END Invalid request type."
            
            request_data = FarmerRequestCreate(
                phone_number=phone_number,
                request_type=selected_type,
                ussd_session_id=session_id,
                status="pending"
            )
            FarmerRequestService(db).create_farmer_request(request_data)
            
            return (
                f"END Your {selected_type} request has been submitted.\n"
                "You will receive a confirmation shortly."
            )
        
        elif inputs[0] == "2" and inputs[1] == "0":
            return (
                "CON Welcome to IvhuRedu\n"
                "1. Submit Request\n"
                "2. Check My Requests"
            )
        else:
            return "END Thank you for using IvhuRedu."

    return "END Thank you for using IvhuRedu."


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