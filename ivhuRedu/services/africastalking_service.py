import os
import re
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

    def _normalize_number(self, num: str) -> Optional[str]:
        """Normalize to E.164 and validate length for common formats."""
        num = num.strip().replace(" ", "").replace("-", "")

        if num.startswith("0"):
            num = "+263" + num[1:]  
        elif not num.startswith("+"):
            num = "+" + num

       
        digits = re.sub(r"[^\d]", "", num)

        if num.startswith("+263") and len(digits) != 12:  
            print(f"Invalid ZW number, wrong length: {num}")
            return None

        return "+" + digits

    def send_sms(self, message: str, recipients: list[str]):
        try:
            response = self.sms.send(message, recipients)
            print(f"SMS sent: {response}")
            return response
        except Exception as e:
            print(f"SMS failed: {e}")
            return None

    def send_bulk_sms(self, phone_numbers: List[str], message: str) -> Optional[dict]:
        formatted_numbers = []
        for num in phone_numbers:
            normalized = self._normalize_number(num)
            if normalized:
                formatted_numbers.append(normalized)
            else:
                print(f"Skipping invalid number: {num}")

        if not formatted_numbers:
            print("No valid numbers to send to.")
            return None

        try:
            response = self.sms.send(message, formatted_numbers)
            return response
        except Exception as e:
            print(f"AT SMS Error: {e}")
            return None

at_service = AfricaTalkingService()

def send_sms(phone_numbers: List[str], message: str) -> Optional[dict]:
    return at_service.send_bulk_sms(phone_numbers, message)
