import os
import africastalking
from typing import List
from dotenv import load_dotenv

load_dotenv()


class AfricaTalkingRepository:
    def __init__(self):
        self.username = os.getenv("AT_USERNAME", "sandbox")
        self.api_key = os.getenv("AT_API_KEY")
        africastalking.initialize(self.username, self.api_key)
        self.sms = africastalking.SMS

    def send(self, message: str, recipients: List[str]):
        """The actual query — sends a request to Africa's Talking's SMS API."""
        try:
            response = self.sms.send(message, recipients)
            print(f"SMS sent: {response}")
            return response
        except Exception as e:
            print(f"SMS failed: {e}")
            return None