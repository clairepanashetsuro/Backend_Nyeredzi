import re
from typing import List, Optional

from ivhuRedu.repositories.africastalking_repository import AfricaTalkingRepository


class AfricaTalkingService:
    def __init__(self):
        self.repo = AfricaTalkingRepository()

    def _normalize_number(self, num: str) -> Optional[str]:
        """Normalize to E.164 and validate length for common formats. (Business logic)"""
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
        return self.repo.send(message, recipients)

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

        return self.repo.send(message, formatted_numbers)


at_service = AfricaTalkingService()


def send_sms(phone_numbers: List[str], message: str) -> Optional[dict]:
    return at_service.send_bulk_sms(phone_numbers, message)