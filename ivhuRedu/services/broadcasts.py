from uuid import UUID
import json
import os
from typing import Optional

from ivhuRedu.utils.sms_logger import log_sms_broadcast, read_sms_log
from ivhuRedu.services.africastalking_service import send_sms

LOG_FILE = "logs/sms_audit.json"


def send_broadcast(
    ward: str,
    message: str,
    farmer_count: int,
    worker_count: int,
    sent_by: UUID,
    sent_by_name: str,
    phone_numbers: list[str]
) -> dict:
    total = farmer_count + worker_count
    sms_result = send_sms(message, phone_numbers)
    status = "SENT" if sms_result["success"] else "FAILED"

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
        raise Exception("SMS sending failed")

    return {
        "status": "success",
        "message": "SMS broadcast sent",
        "ward": ward,
        "total_recipients": total
    }


def sms_callback(phone_number: str, delivery_status: str) -> dict:
    print(f"[SMS DELIVERY] {phone_number}: {delivery_status}")
    return {"received": True}


def get_history() -> list:
    return read_sms_log()


def get_summary() -> dict:
    records = read_sms_log()
    total_broadcasts = len(records)
    total_farmers = sum(r.get("farmers", 0) for r in records)
    total_workers = sum(r.get("workers", 0) for r in records)

    return {
        "total_broadcasts": total_broadcasts,
        "total_farmers": total_farmers,
        "total_workers": total_workers,
        "recent": records[-10:]
    }


def get_broadcast(broadcast_id: str) -> Optional[dict]:
    records = read_sms_log()
    for record in records:
        if record.get("broadcast_id") == broadcast_id:
            return record
    return None


def delete_broadcast(broadcast_id: str) -> bool:
    records = read_sms_log()
    new_records = [r for r in records if r.get("broadcast_id") != broadcast_id]

    if len(new_records) == len(records):
        return False

    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "w") as file:
        json.dump(new_records, file, indent=4)

    return True