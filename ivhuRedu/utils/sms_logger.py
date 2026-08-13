import json
import os
import uuid
from datetime import datetime
from typing import List

LOG_FILE = os.getenv("SMS_AUDIT_LOG_PATH", "logs/sms_audit.json")


def _ensure_dir():
    dir_path = os.path.dirname(LOG_FILE)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


def load_logs() -> List[dict]:
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_logs(logs: List[dict]):
    _ensure_dir()
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4, default=str)


def log_sms_broadcast(
    sent_by, sent_by_name, ward, message,
    recipient_type, farmers, workers, total,
    status, provider_response=None
):
    logs = load_logs()
    broadcast_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    log_entry = {
        "broadcast_id": broadcast_id,
        "sent_by": str(sent_by),
        "sent_by_name": sent_by_name,
        "ward": ward,
        "message": message,
        "recipient_type": recipient_type,
        "farmers": farmers,
        "workers": workers,
        "total_recipients": total,
        "status": status,
        "provider_response": provider_response,
        "created_at": created_at
    }

    logs.append(log_entry)
    save_logs(logs)
    return log_entry


def read_sms_log() -> List[dict]:
    return load_logs()