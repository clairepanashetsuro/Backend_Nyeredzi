import os
import requests


def send_sms(message: str, phone_numbers: list[str]):
    api_key = os.getenv("SMS_LEOPARD_API_KEY")
    api_secret = os.getenv("SMS_LEOPARD_API_SECRET")
    sender_id = os.getenv("SMS_LEOPARD_SENDER_ID")

    if not api_key or not api_secret:
        return {
            "success": False,
            "error": "SMS Leopard credentials are missing."
        }

    try:
        response = requests.post(
            "https://api.smsleopard.com/v1/sms/send",
            headers={"Content-Type": "application/json"},
            auth=(api_key, api_secret),
            json={
                "message": message,
                "recipient": phone_numbers,
                "sender_id": sender_id
            },
            timeout=30
        )

        if response.status_code == 200:
            return {
                "success": True,
                "response": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
