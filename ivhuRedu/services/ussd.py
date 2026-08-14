from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.models.farmer_request import FarmerRequest


class USSDService:
    """Handles Africa's Talking USSD session logic for IvhuRedu."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sms_service = None
        try:
            from ivhuRedu.services.africastalking_service import AfricaTalkingService
            self.sms_service = AfricaTalkingService()
        except Exception as e:
            print(f"SMS service not available: {e}")

    WELCOME_MENU = (
        "CON Welcome to IvhuRedu\n"
        "1. Submit Request\n"
        "2. Check My Requests"
    )

    REQUEST_TYPE_MENU = (
        "CON Select request type:\n"
        "1. Soil Testing\n"
        "2. Seed Supply\n"
        "3. Extension Visit\n"
        "4. Fertilizer Request"
    )

    REQUEST_TYPES = {
        "1": "Soil Testing",
        "2": "Seed Supply",
        "3": "Extension Visit",
        "4": "Fertilizer Request",
    }

    async def handle(self, session_id: str, phone_number: str, text: str) -> str:
        inputs = text.split("*") if text else []
        level = len(inputs)

        if level == 0:
            return self.WELCOME_MENU

        if level == 1:
            if inputs[0] == "1":
                return self.REQUEST_TYPE_MENU
            elif inputs[0] == "2":
                return await self._list_requests(phone_number)
            else:
                return self._end("Invalid selection.")

        if level == 2:
            if inputs[0] == "1":
                return await self._create_request(inputs[1], phone_number, session_id)
            elif inputs[0] == "2" and inputs[1] == "0":
                return self.WELCOME_MENU
            else:
                return self._end("Thank you for using IvhuRedu.")

        return self._end("Thank you for using IvhuRedu.")

    async def _list_requests(self, phone_number: str) -> str:
        try:
            result = await self.db.execute(
                select(FarmerRequest).where(FarmerRequest.phone_number == phone_number)
                .order_by(FarmerRequest.created_at.desc())
            )
            requests = result.scalars().all()

            if not requests:
                return self._end("You have no active requests.")

            lines = ["CON Your Requests:"]
            for idx, req in enumerate(requests[:5], 1):
                lines.append(f"{idx}. {req.request_type} - {req.status}")
            lines.append("0. Back")

            return "\n".join(lines)
        except Exception as e:
            print(f"LIST REQUESTS ERROR: {e}")
            import traceback
            traceback.print_exc()
            return self._end("Error loading requests. Please try again.")

    async def _create_request(self, type_code: str, phone_number: str, session_id: str) -> str:
        request_type = self.REQUEST_TYPES.get(type_code)
        if not request_type:
            return self._end("Invalid request type.")

        try:
            db_request = FarmerRequest(
                phone_number=phone_number,
                request_type=request_type,
                ussd_session_id=session_id,
                status="pending",
            )
            self.db.add(db_request)
            await self.db.commit()
            await self.db.refresh(db_request)

            if self.sms_service:
                try:
                    message = (
                        f"IvhuRedu: Your {request_type} request has been received. "
                        f"Request ID: {db_request.request_id}. "
                        "You will be contacted shortly."
                    )
                    self.sms_service.send_sms(message, [phone_number])
                except Exception as sms_error:
                    print(f"SMS sending failed: {sms_error}")

            return self._end(
                f"Your {request_type} request has been submitted.\n"
                "You will receive a confirmation shortly."
            )
        except Exception as e:
            print(f"CREATE REQUEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            return self._end("Request could not be saved. Please try again.")

    @staticmethod
    def _end(message: str) -> str:
        return f"END {message}"