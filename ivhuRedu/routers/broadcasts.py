from fastapi import APIRouter, HTTPException, Request
from uuid import UUID

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


@router.post("/send")
async def send_broadcast(
    ward: str,
    message: str,
    farmer_count: int,
    worker_count: int,
    sent_by: UUID,
    sent_by_name: str,
    phone_numbers: list[str]
):
    try:
        return service_send_broadcast(
            ward=ward,
            message=message,
            farmer_count=farmer_count,
            worker_count=worker_count,
            sent_by=sent_by,
            sent_by_name=sent_by_name,
            phone_numbers=phone_numbers
        )
    except Exception:
        raise HTTPException(status_code=500, detail="SMS sending failed")


@router.post("/sms/callback")
async def sms_callback(request: Request):
    data = await request.json()
    return service_sms_callback(
        phone_number=data.get("phoneNumber"),
        delivery_status=data.get("status")
    )


@router.get("/history")
def history():
    return get_history()


@router.get("/summary")
def summary():
    return get_summary()


@router.get("/{broadcast_id}")
def broadcast_detail(broadcast_id: str):
    record = get_broadcast(broadcast_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return record


@router.delete("/{broadcast_id}")
def delete_broadcast_route(broadcast_id: str):
    if not delete_broadcast(broadcast_id):
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return {"message": "Broadcast deleted"}