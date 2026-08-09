from fastapi import APIRouter, HTTPException, Request
from uuid import UUID
from typing import List

from ivhuRedu.schemas.broadcast import (
    BroadcastCreate,
    BroadcastResponse,
    BroadcastSummaryResponse
)
from ivhuRedu.services.broadcasts import (
    send_broadcast as service_send_broadcast,
    sms_callback as service_sms_callback,
    get_history,
    get_summary,
    get_broadcast,
    delete_broadcast,
)

router = APIRouter(
    prefix="/broadcasts",
    tags=["Broadcasts"]
)

@router.post("/send", response_model=BroadcastResponse, status_code=201)
async def send_broadcast(data: BroadcastCreate):
    try:
        return service_send_broadcast(
            ward=data.ward,
            message=data.message,
            recipient_type=data.recipient_type,
            farmer_count=data.farmer_count,
            worker_count=data.worker_count,
            sent_by=data.sent_by,
            sent_by_name=data.sent_by_name,
            phone_numbers=data.phone_numbers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMS sending failed: {str(e)}")

@router.post("/sms/callback")
async def sms_callback(request: Request):
    data = await request.json()
    return service_sms_callback(
        phone_number=data.get("phoneNumber"),
        delivery_status=data.get("status")
    )

@router.get("/history", response_model=List[dict])
async def history():
    return get_history()

@router.get("/summary", response_model=BroadcastSummaryResponse)
async def summary():
    return get_summary()

@router.get("/{broadcast_id}", response_model=dict)
async def broadcast_detail(broadcast_id: str):
    record = get_broadcast(broadcast_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return record

@router.delete("/{broadcast_id}")
async def delete_broadcast_route(broadcast_id: str):
    if not delete_broadcast(broadcast_id):
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return {"message": "Broadcast deleted"}
