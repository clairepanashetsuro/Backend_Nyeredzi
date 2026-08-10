import json
import os
from uuid import UUID
from typing import Optional, List

from ivhuRedu.utils.sms_logger import log_sms_broadcast, read_sms_log
from ivhuRedu.services.africastalking_service import send_sms

LOG_FILE = "logs/sms_audit.json"


class SMSBroadcastError(Exception):
    pass


def send_broadcast(
    ward: str,
    message: str,
    recipient_type: str,
    farmer_count: int,
    worker_count: int,
    sent_by: UUID,
    sent_by_name: str,
    phone_numbers: List[str]
) -> dict:
    total = farmer_count + worker_count

    sms_result = send_sms(message, phone_numbers)
    status = "SENT" if sms_result.get("success") else "FAILED"

    provider_response = (
        str(sms_result.get("response"))
        if sms_result.get("success")
        else sms_result.get("error", "Unknown error")
    )

    log_entry = log_sms_broadcast(
        sent_by=sent_by,
        sent_by_name=sent_by_name,
        ward=ward,
        message=message,
        recipient_type=recipient_type,
        farmers=farmer_count,
        workers=worker_count,
        total=total,
        status=status,
        provider_response=provider_response
    )

    if status == "FAILED":
        raise SMSBroadcastError("SMS sending failed")

    return {
        "broadcast_id": log_entry["broadcast_id"],
        "status": "success",
        "message": "SMS broadcast sent",
        "ward": log_entry["ward"],
        "recipient_type": log_entry["recipient_type"],
        "total_recipients": log_entry["total_recipients"],
        "sent_by": log_entry["sent_by"],
        "sent_by_name": log_entry["sent_by_name"],
        "created_at": log_entry["created_at"]
    }


def sms_callback(payload: dict) -> dict:
    phone_number = payload.get("phoneNumber")
    delivery_status = payload.get("status")

    print(f"[SMS DELIVERY] {phone_number}: {delivery_status}")

    return {
        "received": True,
        "phone_number": phone_number,
        "status": delivery_status
    }


def get_history() -> List[dict]:
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
        "recent": records[-10:] if records else []
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