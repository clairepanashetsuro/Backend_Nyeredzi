import os
import africastalking


def send_sms(message: str, phone_numbers: list[str]):

    username = os.getenv("AT_USERNAME")
    api_key = os.getenv("AT_API_KEY")

    if not username or not api_key:
        return {
            "success": False,
            "error": "Africa's Talking credentials are missing."
        }

    try:
        africastalking.initialize(username, api_key)

        sms = africastalking.SMS

        response = sms.send(
            message,
            phone_numbers
        )

        return {
            "success": True,
            "response": response
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        };