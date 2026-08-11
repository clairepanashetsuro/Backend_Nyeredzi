import os
from typing import List, Optional
import africastalking
from dotenv import load_dotenv

load_dotenv()

class AfricaTalkingService:
    def __init__(self):
        self.username = os.getenv("AT_USERNAME", "sandbox")
        self.api_key = os.getenv("AT_API_KEY")
        africastalking.initialize(self.username, self.api_key)
        self.sms = africastalking.SMS



    def send_sms(self, message: str, recipients: list[str]):
        try:
            response = self.sms.send(message, recipients)
            print(f"SMS sent: {response}")
            return response
        except Exception as e:
            print(f"SMS failed: {e}")
            return None
        
    def send_bulk_sms(self, phone_numbers: List[str], message: str) -> Optional[dict]:
        try:
            formatted_numbers = [
                num if num.startswith("+") else f"+{num}" 
                for num in phone_numbers
            ]
            response = self.sms.send(message, formatted_numbers)
            return response
        except Exception as e:
            print(f"AT SMS Error: {e}")
            return None

at_service = AfricaTalkingService()

def send_sms(phone_numbers: List[str], message: str) -> Optional[dict]:
    return at_service.send_bulk_sms(phone_numbers, message)