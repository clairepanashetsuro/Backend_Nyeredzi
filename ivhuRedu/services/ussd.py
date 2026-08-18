from sqlalchemy.ext.asyncio import AsyncSession

from ivhuRedu.repositories.farmer_request import (
    FarmerRequestRepository,
)


class USSDService:
    """Handles Africa's Talking USSD session logic for IvhuRedu."""

    def __init__(self, db: AsyncSession):
        self.db = db

        self.farmer_request_repository = (
            FarmerRequestRepository(db)
        )

        self.sms_service = None

        try:
            from ivhuRedu.services.africastalking_service import (
                AfricaTalkingService,
            )

            self.sms_service = AfricaTalkingService()

        except Exception as e:
            print(f"SMS service not available: {e}")


    MAIN_MENU = (
        "CON Welcome to IvhuRedu\n"
        "1. Extension worker\n"
        "2. Farmer"
    )

    PIN_MENU = (
        "CON Enter 4 digit code"
    )


    FARMER_MENU = (
        "CON Select option:\n"
        "1. Report land Degradation in your area\n"
        "2. Request visit\n"
        "3. Land care tips\n"
        "4. View Reports"
    )

    REPORT_FOR_MENU = (
        "CON Report Issue For:\n"
        "1. Farmer\n"
        "2. Ward"
    )

    FARMER_ISSUE_MENU = (
        "CON Select Issue:\n"
        "1. Pest disease outbreak\n"
        "2. Crop failure\n"
        "3. Gully Erosion\n"
        "4. Soil Fertility Decline"
    )

    WARD_ISSUE_MENU = (
        "CON Select Issue:\n"
        "1. Pest disease outbreak\n"
        "2. Drought crop failure\n"
        "3. Gully Erosion\n"
        "4. Dam Siltation\n"
        "5. Illegal land clearing"
    )

    ENVIRONMENT_ISSUE_MENU = (
        "CON Select issue:\n"
        "1. Soil erosion\n"
        "2. Deforestation\n"
        "3. Salination\n"
        "4. Illegal Sand Mining"
    )

    LAND_ASSESSMENT_MENU = (
        "CON Select issue:\n"
        "1. Land restoration Review\n"
        "2. Soil testing\n"
        "3. General land assessment\n"
        "4. Pest and Diseases"
    )


    LAND_CARE_MENU = (
        "CON Select issue:\n"
        "1. Fixing gullies\n"
        "2. Soil protecting\n"
        "3. Tree planting\n"
        "4. Fire protection\n"
        "5. Fertilizer Application"
    )

    LANGUAGE_MENU = (
        "CON Select Language:\n"
        "1. Shona\n"
        "2. English"
    )

    PEST_THREAT_MENU = (
        "CON Select threat:\n"
        "1. Fall army worm\n"
        "2. Locust swan\n"
        "3. Maize Streak Virus\n"
        "4. Weevils & Borers"
    )

    CROP_THREAT_MENU = (
        "CON Select Threat:\n"
        "1. Crop wilting and dying\n"
        "2. Severe water stress\n"
        "3. Live stock water crisis"
    )

    VILLAGE_MENU = (
        "CON Select Village:\n"
        "1. Village 1\n"
        "2. Village 2\n"
        "3. Village 3"
    )

    IMPACT_MENU = (
        "CON Select impact Level:\n"
        "1. Extreme\n"
        "2. High\n"
        "3. Medium\n"
        "4. Low"
    )
    async def handle(
        self,
        session_id: str,
        phone_number: str,
        text: str,
    ) -> str:

        phone_number = self._normalize_phone_number(
            phone_number
        )

        inputs = text.split("*") if text else []

        if not inputs:
            return self.MAIN_MENU


        if len(inputs) == 1:

            if inputs[0] == "1":
                return self._end(
                    "Extension worker services are currently "
                    "unavailable."
                )

            if inputs[0] == "2":
                registered = (
                    await self
                    .farmer_request_repository
                    .is_registered_farmer(phone_number)
                )

                if not registered:
                    return self._end(
                        "This phone number is not registered "
                        "with IvhuRedu. Please register first."
                    )

                return self.PIN_MENU

            return self._end(
                "Invalid selection."
            )

        if len(inputs) == 2:

            if inputs[0] != "2":
                return self._end(
                    "Invalid session."
                )

            pin = inputs[1]

            if not self._is_valid_pin(pin):
                return self._end(
                    "Invalid code. Please enter a 4 digit code."
                )

            valid_pin = (
                await self
                .farmer_request_repository
                .verify_farmer_pin(
                    phone_number,
                    pin,
                )
            )

            if not valid_pin:
                return self._end(
                    "Incorrect code. Please try again."
                )

            return self.FARMER_MENU

        if len(inputs) == 3:

            if inputs[0] != "2":
                return self._end(
                    "Invalid session."
                )

            option = inputs[2]

            if option == "1":
                return self.REPORT_FOR_MENU

            if option == "2":
                return self.LAND_ASSESSMENT_MENU

            if option == "3":
                return self.LAND_CARE_MENU

            if option == "4":
                return await self._view_reports(
                    phone_number
                )

            return self._end(
                "Invalid selection."
            )

        if len(inputs) == 4:

            if inputs[2] != "1":
                return self._end(
                    "Invalid session."
                )

            report_for = inputs[3]

            if report_for == "1":
                return self.FARMER_ISSUE_MENU

            if report_for == "2":
                return self.WARD_ISSUE_MENU

            return self._end(
                "Invalid selection."
            )

        if len(inputs) == 5:

            if inputs[2] != "1":
                return self._end(
                    "Invalid session."
                )

            report_for = inputs[3]
            issue = inputs[4]

            if report_for == "1":

                if issue not in [
                    "1",
                    "2",
                    "3",
                    "4",
                ]:
                    return self._end(
                        "Invalid issue."
                    )

                return self.LANGUAGE_MENU

            if report_for == "2":

                if issue not in [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                ]:
                    return self._end(
                        "Invalid issue."
                    )

                return self.LANGUAGE_MENU

            return self._end(
                "Invalid selection."
            )

        if len(inputs) == 6:

            language = inputs[5]

            if language not in ["1", "2"]:
                return self._end(
                    "Invalid language."
                )

            report_for = inputs[3]
            issue = inputs[4]

            if issue == "1":
                return self.PEST_THREAT_MENU

            if issue == "2":
                return self.CROP_THREAT_MENU

            if issue in ["3", "4", "5"]:
                return self.VILLAGE_MENU

            return self._end(
                "Invalid selection."
            )


        if len(inputs) == 7:

            report_for = inputs[3]
            issue = inputs[4]
            threat = inputs[6]

            if issue == "1":

                if threat not in [
                    "1",
                    "2",
                    "3",
                    "4",
                ]:
                    return self._end(
                        "Invalid threat."
                    )

                return self.VILLAGE_MENU

            if issue == "2":

                if threat not in [
                    "1",
                    "2",
                    "3",
                ]:
                    return self._end(
                        "Invalid threat."
                    )

                return self.VILLAGE_MENU

            return self._end(
                "Invalid selection."
            )

        if len(inputs) == 8:

            village = inputs[7]

            if village not in [
                "1",
                "2",
                "3",
            ]:
                return self._end(
                    "Invalid village."
                )

            return self.IMPACT_MENU

        if len(inputs) == 9:

            impact = inputs[8]

            if impact not in [
                "1",
                "2",
                "3",
                "4",
            ]:
                return self._end(
                    "Invalid impact level."
                )

            return (
                "CON Enter Farmer Phone's Number"
            )

        if len(inputs) == 10:

            farmer_phone = self._normalize_phone_number(
                inputs[9]
            )

            if not farmer_phone:
                return self._end(
                    "Invalid farmer phone number."
                )

            return (
                "CON Enter ward number"
            )


        if len(inputs) == 11:

            ward_number = inputs[10]

            if not ward_number:
                return self._end(
                    "Invalid ward number."
                )

            return await self._save_land_degradation_report(
                session_id=session_id,
                reporter_phone=phone_number,
                farmer_phone=inputs[9],
                ward_number=ward_number,
                inputs=inputs,
            )

        return self._end(
            "Invalid USSD session."
        )


    async def _save_land_degradation_report(
        self,
        session_id: str,
        reporter_phone: str,
        farmer_phone: str,
        ward_number: str,
        inputs: list,
    ) -> str:

        try:

            report_for = inputs[3]
            issue = inputs[4]
            language = inputs[5]
            village = inputs[7]
            impact = inputs[8]

            threat = None

            if len(inputs) > 6:
                threat = inputs[6]

            issue_names = {
                "1": "Pest disease outbreak",
                "2": "Crop failure",
                "3": "Gully Erosion",
                "4": "Soil Fertility Decline",
                "5": "Illegal land clearing",
            }

            language_names = {
                "1": "Shona",
                "2": "English",
            }

            village_names = {
                "1": "Village 1",
                "2": "Village 2",
                "3": "Village 3",
            }

            impact_names = {
                "1": "Extreme",
                "2": "High",
                "3": "Medium",
                "4": "Low",
            }

            threat_names = {
                "1": "Fall army worm",
                "2": "Locust swan",
                "3": "Maize Streak Virus",
                "4": "Weevils & Borers",
            }

            request_type = "Land Degradation Report"

            description = (
                f"Report For: "
                f"{'Farmer' if report_for == '1' else 'Ward'}\n"
                f"Issue: {issue_names.get(issue, issue)}\n"
                f"Language: "
                f"{language_names.get(language, language)}\n"
                f"Threat: "
                f"{threat_names.get(threat, threat) if threat else 'N/A'}\n"
                f"Village: "
                f"{village_names.get(village, village)}\n"
                f"Impact Level: "
                f"{impact_names.get(impact, impact)}\n"
                f"Affected Farmer Phone: {farmer_phone}\n"
                f"Ward: {ward_number}"
            )

            request_data = {
                "phone_number": reporter_phone,
                "request_type": request_type,
                "description": description,
                "location": ward_number,
                "ussd_session_id": session_id,
                "status": "pending",
            }

            request = (
                await self
                .farmer_request_repository
                .create(request_data)
            )

            if self.sms_service:

                try:

                    message = (
                        "IvhuRedu: Your land degradation "
                        "report has been received. "
                        f"Request ID: {request.request_id}."
                    )

                    self.sms_service.send_sms(
                        message,
                        [reporter_phone],
                    )

                except Exception as sms_error:

                    print(
                        f"SMS sending failed: "
                        f"{sms_error}"
                    )

            return self._end(
                "Your land degradation report has "
                "been submitted successfully."
            )

        except Exception as e:

            print(
                f"LAND DEGRADATION REPORT ERROR: {e}"
            )

            import traceback

            traceback.print_exc()

            return self._end(
                "Report could not be submitted. "
                "Please try again."
            )

    async def _view_reports(
        self,
        phone_number: str,
    ) -> str:

        try:

            reports = (
                await self
                .farmer_request_repository
                .get_by_phone(phone_number)
            )

            if not reports:
                return self._end(
                    "You have no reports."
                )

            lines = [
                "CON Your Reports:"
            ]

            for index, report in enumerate(
                reports[:5],
                1,
            ):

                lines.append(
                    f"{index}. "
                    f"{report.request_type} - "
                    f"{report.status}"
                )

            lines.append("0. Back")

            return "\n".join(lines)

        except Exception as e:

            print(
                f"VIEW REPORTS ERROR: {e}"
            )

            return self._end(
                "Unable to load reports."
            )

    @staticmethod
    def _is_valid_pin(pin: str) -> bool:

        return (
            len(pin) == 4
            and pin.isdigit()
        )

    @staticmethod
    def _normalize_phone_number(
        phone_number: str,
    ) -> str:

        if not phone_number:
            return ""

        phone_number = phone_number.strip()

        if phone_number.startswith("+"):
            return phone_number

        if phone_number.startswith("263"):
            return f"+{phone_number}"

        if phone_number.startswith("0"):
            return f"+263{phone_number[1:]}"

        return phone_number

    @staticmethod
    def _end(
        message: str,
    ) -> str:

        return f"END {message}"

    