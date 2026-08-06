from fastapi import APIRouter, HTTPException
from uuid import UUID

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
        status="SENT"

    else:
        status="FAILED"


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


    if status=="FAILED":
        raise HTTPException(
            status_code=500,
            detail="SMS sending failed"
        )


    return {
        "status":"success",
        "message":"SMS broadcast sent",
        "ward":ward,
        "total_recipients":total
    }

@router.get("/history")
def history():
    records = read_sms_log()
    return records


@router.get("/summary")
def summary():
    records = read_sms_log()
    total_broadcasts = len(records)

    total_farmers = sum(
        r.get("farmers",0)
        for r in records
    )

    total_workers = sum(
        r.get("workers",0)
        for r in records
    )

    return {
        "total_broadcasts": total_broadcasts,
        "total_farmers": total_farmers,
        "total_workers": total_workers,
        "recent": records[-10:]
    }

