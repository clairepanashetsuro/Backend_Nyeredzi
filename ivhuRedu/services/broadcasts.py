import re
from uuid import UUID
from typing import Optional, List

from ivhuRedu.utils.sms_logger import log_sms_broadcast, read_sms_log, save_logs
from ivhuRedu.services.sms_leopard import send_sms


class SMSBroadcastValidationError(Exception):
    pass


class SMSBroadcastError(Exception):
    pass


def _validate_phone_number(phone: str) -> bool:
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))


def _validate_inputs(
    ward: str,
    message: str,
    recipient_type: str,
    farmer_count: int,
    worker_count: int,
    sent_by_name: str,
    phone_numbers: List[str]
) -> None:
    if not ward or not ward.strip():
        raise SMSBroadcastValidationError("Ward is required")

    if not message or not message.strip():
        raise SMSBroadcastValidationError("Message is required")

    if len(message.strip()) > 1600:
        raise SMSBroadcastValidationError("Message exceeds maximum length of 1600 characters")

    if not sent_by_name or not sent_by_name.strip():
        raise SMSBroadcastValidationError("Sender name is required")

    valid_types = {"farmers", "workers", "all"}
    if recipient_type not in valid_types:
        raise SMSBroadcastValidationError(
            f"Invalid recipient_type. Must be one of: {valid_types}"
        )

    if farmer_count < 0:
        raise SMSBroadcastValidationError("Farmer count cannot be negative")

    if worker_count < 0:
        raise SMSBroadcastValidationError("Worker count cannot be negative")

    if not phone_numbers:
        raise SMSBroadcastValidationError("At least one phone number is required")

    for phone in phone_numbers:
        if not _validate_phone_number(phone):
            raise SMSBroadcastValidationError(
                f"Invalid phone number format: {phone}. Use E.164 format (e.g. +263772123456)"
            )


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
    _validate_inputs(
        ward=ward,
        message=message,
        recipient_type=recipient_type,
        farmer_count=farmer_count,
        worker_count=worker_count,
        sent_by_name=sent_by_name,
        phone_numbers=phone_numbers
    )

    total = farmer_count + worker_count

    sms_result = send_sms(message.strip(), phone_numbers)
    status = "SENT" if sms_result.get("success") else "FAILED"

    provider_response = (
        str(sms_result.get("response"))
        if sms_result.get("success")
        else sms_result.get("error", "Unknown error")
    )

    log_entry = log_sms_broadcast(
        sent_by=sent_by,
        sent_by_name=sent_by_name.strip(),
        ward=ward.strip(),
        message=message.strip(),
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
    if not isinstance(payload, dict):
        return {"received": False, "error": "Invalid payload format"}

    phone_number = payload.get("phoneNumber")
    delivery_status = payload.get("status")

    if not phone_number or not isinstance(phone_number, str):
        return {"received": False, "error": "Missing or invalid phoneNumber"}

    if not delivery_status or not isinstance(delivery_status, str):
        return {"received": False, "error": "Missing or invalid status"}

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
    if not broadcast_id or not isinstance(broadcast_id, str):
        return None

    records = read_sms_log()
    for record in records:
        if record.get("broadcast_id") == broadcast_id:
            return record
    return None


def delete_broadcast(broadcast_id: str) -> bool:
    if not broadcast_id or not isinstance(broadcast_id, str):
        return False

    records = read_sms_log()
    new_records = [r for r in records if r.get("broadcast_id") != broadcast_id]

    if len(new_records) == len(records):
        return False

    save_logs(new_records)
    return True
