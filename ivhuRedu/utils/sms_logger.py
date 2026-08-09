import json
import os
from datetime import datetime


LOG_FILE = "logs/sms_audit.json"


def log_sms_broadcast(
    sent_by,
    sent_by_name,
    ward,
    message,
    farmers,
    workers,
    total,
    status
):
    if hasattr(sent_by, 'hex'):
        sent_by = str(sent_by)

    record = {
        "broadcast_id": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "sent_by": sent_by,
        "sent_by_name": sent_by_name,
        "ward": ward,
        "message": message,
        "farmers": farmers,
        "workers": workers,
        "total_recipients": total,
        "status": status,
        "created_at": datetime.utcnow().isoformat()
    }

    os.makedirs("logs", exist_ok=True)

    data = []
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
        try:
            with open(LOG_FILE, "r") as file:
                data = json.load(file)
                if not isinstance(data, list):
                    data = []
        except (json.JSONDecodeError, ValueError):
            data = []

    data.append(record)

    with open(LOG_FILE, "w") as file:
        json.dump(data, file, indent=4)


def read_sms_log():
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r") as file:
            return json.load(file)
    except (json.JSONDecodeError, ValueError):
        return []