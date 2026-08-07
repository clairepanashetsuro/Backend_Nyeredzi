from fastapi import APIRouter, HTTPException, Request
from uuid import UUID
import json
import os

from ivhuRedu.utils.sms_logger import (
    log_sms_broadcast,
    read_sms_log
)

from ivhuRedu.services.africastalking_service import send_sms

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
    
    total = farmer_count + worker_count

    sms_result = send_sms(
        message,
        phone_numbers
    )

    if sms_result["success"]:
        status = "SENT"
    else:
        status = "FAILED"

    log_sms_broadcast(
        sent_by=sent_by,
        sent_by_name=sent_by_name,
        ward=ward,
        message=message,
        farmers=farmer_count,
        workers=worker_count,
        total=total,
        status=status
    )

    if status == "FAILED":
        raise HTTPException(
            status_code=500,
            detail="SMS sending failed"
        )

    return {
        "status": "success",
        "message": "SMS broadcast sent",
        "ward": ward,
        "total_recipients": total
    }

@router.post("/sms/callback")
async def sms_callback(request: Request):
    data = await request.json()
    phone_number = data.get("phoneNumber")
    delivery_status = data.get("status")
    print(f"[SMS DELIVERY] {phone_number}: {delivery_status}")
    return {"received": True}

@router.get("/history")
def history():
    records = read_sms_log()
    return records

@router.get("/summary")
def summary():
    records = read_sms_log()
    total_broadcasts = len(records)

    total_farmers = sum(
        r.get("farmers", 0)
        for r in records
    )

    total_workers = sum(
        r.get("workers", 0)
        for r in records
    )

    return {
        "total_broadcasts": total_broadcasts,
        "total_farmers": total_farmers,
        "total_workers": total_workers,
        "recent": records[-10:]
    }

@router.get("/{broadcast_id}")
def get_broadcast(broadcast_id: str):
    records = read_sms_log()
    for record in records:
        if record.get("broadcast_id") == broadcast_id:
            return record
    raise HTTPException(status_code=404, detail="Broadcast not found")

@router.delete("/{broadcast_id}")
def delete_broadcast(broadcast_id: str):
    records = read_sms_log()
    new_records = [r for r in records if r.get("broadcast_id") != broadcast_id]
    
    if len(new_records) == len(records):
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    LOG_FILE = "logs/sms_audit.json"
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "w") as file:
        json.dump(new_records, file, indent=4)
    
    return {"message": "Broadcast deleted"}
