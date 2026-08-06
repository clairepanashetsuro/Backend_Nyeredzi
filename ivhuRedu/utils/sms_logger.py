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

    record = {

        "broadcast_id":
            datetime.utcnow().strftime("%Y%m%d%H%M%S"),

        "sent_by": sent_by,

        "sent_by_name": sent_by_name,

        "ward": ward,

        "message": message,

        "farmers": farmers,

        "workers": workers,

        "total_recipients": total,

        "status": status,

        "created_at":
            datetime.utcnow().isoformat()

    }


    os.makedirs(
        "logs",
        exist_ok=True
    )


    if os.path.exists(LOG_FILE):

        with open(LOG_FILE,"r") as file:
            data=json.load(file)

    else:

        data=[]


    data.append(record)


    with open(LOG_FILE,"w") as file:

        json.dump(
            data,
            file,
            indent=4
        )



def read_sms_log():

    if not os.path.exists(LOG_FILE):

        return []


    with open(LOG_FILE,"r") as file:

        return json.load(file)