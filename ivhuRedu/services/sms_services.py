import os
import base64
import secrets
import uuid
import logging
import asyncio
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException

logger = logging.getLogger("uvicorn.error")


class SMSService:
    def __init__(self):
        self.api_key = (os.getenv("SMS_LEOPARD_API_KEY") or "").strip().strip('"').strip("'")
        self.api_secret = (os.getenv("SMS_LEOPARD_API_SECRET") or "").strip().strip('"').strip("'")
        self.sender_id = (os.getenv("SMS_LEOPARD_SENDER_ID") or "AkiraChix").strip().strip('"').strip("'")
        self.callback_secret = (os.getenv("SMS_CALLBACK_SECRET") or "my_super_secret_webhook_token_123").strip().strip('"').strip("'")
        self.url = "https://api.smsleopard.com/v1/sms/send"
        self.status_url = os.getenv("SMS_STATUS_CALLBACK_URL")
        self.otp_store: Dict[str, Dict[str, Any]] = {}
        self.logs: Dict[str, Dict[str, Any]] = {}

    def _basic_auth_header(self):
        credentials = f"{self.api_key}:{self.api_secret}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"

    def _headers(self):
        return {
            "Authorization": self._basic_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _send(self, destination: Any, message: str, sender_id: Optional[str]) -> Dict[str, Any]:
        if not self.api_key or not self.api_secret:
            raise HTTPException(status_code=503, detail="SMS Leopard credentials not configured")

        payload: Dict[str, Any] = {
            "message": message,
            "destination": destination if isinstance(destination, list) else [{"number": destination}],
        }
        if sender_id or self.sender_id:
            payload["source"] = sender_id or self.sender_id
        if self.status_url:
            payload["status_url"] = self.status_url
            payload["status_secret"] = self.callback_secret

        def _post():
            return requests.post(self.url, headers=self._headers(), json=payload, timeout=30)

        try:
            response = await asyncio.to_thread(_post)
            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                return {"status": "success", "raw_response": response.text}
        except requests.exceptions.HTTPError as exc:
            logger.error(f"SMS Leopard HTTP error: {exc.response.text}")
            raise HTTPException(
                status_code=502,
                detail=f"SMS Leopard rejected the request: {exc.response.text}",
            )
        except Exception as exc:
            logger.error(f"SMS Leopard connection error: {exc}")
            raise HTTPException(
                status_code=503,
                detail=f"Could not connect to SMS Leopard: {exc}",
            )

    def _log(self, entry: dict) -> str:
        log_id = str(uuid.uuid4())
        entry["id"] = log_id
        entry["created_at"] = datetime.now(timezone.utc)
        self.logs[log_id] = entry
        return log_id

    def _ip(self, http_request: Optional[Any]) -> Optional[str]:
        if http_request is None:
            return None
        client = getattr(http_request, "client", None)
        return getattr(client, "host", None) if client else None

    def _filter(self, filters: Any):
        results = []
        for log in self.logs.values():
            if filters.status and filters.status.lower() not in log.get("status", "").lower():
                continue
            if filters.message_type and filters.message_type.lower() not in log.get("type", "").lower():
                continue
            if filters.phone_number and filters.phone_number not in log.get("recipients", ""):
                continue
            if filters.sender_id and filters.sender_id.lower() not in str(log.get("sender_id", "")).lower():
                continue
            if filters.ip_address and filters.ip_address != log.get("ip"):
                continue
            if filters.older_than_days is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=filters.older_than_days)
                if log.get("created_at") and log["created_at"] > cutoff:
                    continue
            results.append(log)
        return results

    async def send_sms(self, request: Any, http_request: Optional[Any] = None) -> Dict[str, Any]:
        resp = await self._send([{"number": request.phone_number}], request.message, request.sender_id)
        log_id = self._log({
            "type": "sms",
            "recipients": request.phone_number,
            "message": request.message,
            "status": "sent",
            "sender_id": request.sender_id or self.sender_id,
            "ip": self._ip(http_request),
            "provider_response": resp,
            "external_id": (
                (resp.get("recipients") or [{}])[0].get("id")
                or resp.get("message_id")
                or resp.get("id")
            ),
        })
        return {
            "success": True,
            "message": "SMS sent successfully",
            "log_id": log_id,
            "provider_response": resp,
            "recipient": request.phone_number,
        }

    async def send_alert(self, request: Any, http_request: Optional[Any] = None) -> Dict[str, Any]:
        destinations = [{"number": p} for p in request.phone_numbers]
        resp = await self._send(destinations, request.message, request.sender_id)
        log_id = self._log({
            "type": "alert",
            "recipients": ",".join(request.phone_numbers),
            "message": request.message,
            "status": "sent",
            "sender_id": request.sender_id or self.sender_id,
            "ip": self._ip(http_request),
            "provider_response": resp,
            "external_id": (
                (resp.get("recipients") or [{}])[0].get("id")
                or resp.get("message_id")
                or resp.get("id")
            ),
        })
        return {
            "success": True,
            "message": f"Alert sent to {len(request.phone_numbers)} recipient(s)",
            "log_id": log_id,
            "recipients_count": len(request.phone_numbers),
            "provider_response": resp,
        }

    async def send_otp(self, request: Any, http_request: Optional[Any] = None) -> Dict[str, Any]:
        otp = str(secrets.randbelow(900000) + 100000)
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)

        self.otp_store[request.phone_number] = {
            "otp": otp,
            "expires_at": expires,
        }

        message = f"Your OTP code is {otp}. It expires in 5 minutes."
        resp = await self._send([{"number": request.phone_number}], message, request.sender_id)

        log_id = self._log({
            "type": "otp",
            "recipients": request.phone_number,
            "message": message,
            "status": "sent",
            "sender_id": request.sender_id or self.sender_id,
            "ip": self._ip(http_request),
            "provider_response": resp,
            "external_id": (
                (resp.get("recipients") or [{}])[0].get("id")
                or resp.get("message_id")
                or resp.get("id")
            ),
        })

        return {
            "success": True,
            "status": "queued",
            "log_id": log_id,
            "recipient": request.phone_number,
            "provider_response": resp,
        }

    async def verify_otp(self, request: Any, http_request: Optional[Any] = None) -> Dict[str, Any]:
        stored = self.otp_store.get(request.phone_number)

        if not stored:
            raise HTTPException(status_code=400, detail="No OTP found for this phone number")

        if datetime.now(timezone.utc) >= stored["expires_at"]:
            del self.otp_store[request.phone_number]
            raise HTTPException(status_code=400, detail="OTP has expired")

        if not secrets.compare_digest(stored["otp"], str(request.code)):
            raise HTTPException(status_code=400, detail="Invalid OTP code")

        del self.otp_store[request.phone_number]
        return {"success": True, "message": "OTP verified successfully"}

    async def get_logs(self, filters: Any) -> Dict[str, Any]:
        logs = self._filter(filters)
        logs.sort(
            key=lambda x: x.get("created_at", datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True,
        )
        total = len(logs)

        output_logs = []
        for log in logs:
            cleaned = dict(log)
            if isinstance(cleaned.get("created_at"), datetime):
                cleaned["created_at"] = cleaned["created_at"].isoformat()
            output_logs.append(cleaned)

        return {"logs": output_logs, "total": total}

    async def delete_logs(self, filters: Any) -> Dict[str, Any]:
        if not any([filters.status, filters.message_type, filters.phone_number, filters.sender_id, filters.ip_address, filters.older_than_days is not None]):
            raise HTTPException(
                status_code=400,
                detail="At least one filter parameter is required for deletion",
            )

        to_del = [log["id"] for log in self._filter(filters)]
        for lid in to_del:
            del self.logs[lid]

        return {"success": True, "deleted_count": len(to_del)}

    async def patch_logs(self, patch_data: Any, filters: Any) -> Dict[str, Any]:
        patch_dict = patch_data.model_dump(exclude_unset=True) if hasattr(patch_data, "model_dump") else dict(patch_data)
        updated = 0
        for log in self._filter(filters):
            if "status" in patch_dict and patch_dict["status"] is not None:
                log["status"] = patch_dict["status"]
                log["updated_at"] = datetime.now(timezone.utc)
                updated += 1
        return {"success": True, "updated_count": updated}

    async def get_history(self, limit: int = 100) -> Dict[str, Any]:
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
        logs = sorted(
            self.logs.values(),
            key=lambda x: x.get("created_at", datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True,
        )
        output = []
        for log in logs[:limit]:
            item = dict(log)
            if isinstance(item.get("created_at"), datetime):
                item["created_at"] = item["created_at"].isoformat()
            output.append(item)
        return {"history": output}

    async def get_summary(self) -> Dict[str, Any]:
        sent = 0
        failed = 0
        for log in self.logs.values():
            st = log.get("status", "").lower()
            if st in ("sent", "delivered"):
                sent += 1
            elif st == "failed":
                failed += 1
        return {"total_sent": sent, "total_failed": failed}

    async def handle_callback(self, payload: Any, request: Any) -> Dict[str, Any]:
        provided_secret = None

        if hasattr(request, "query_params"):
            provided_secret = request.query_params.get("secret")
        elif isinstance(request, str):
            provided_secret = request

        if not provided_secret:
            raise HTTPException(
                status_code=401,
                detail="Missing webhook secret query parameter"
            )

        if not secrets.compare_digest(provided_secret, self.callback_secret):
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook secret"
            )

        payload_dict = (
            payload.model_dump()
            if hasattr(payload, "model_dump")
            else dict(payload)
        )

        message_id = payload_dict.get("message_id")
        new_status = payload_dict.get("status", "unknown")

        if message_id:
            for log in self.logs.values():

                # Match future logs through external_id.
                if log.get("external_id") == message_id:
                    log["status"] = new_status
                    log["updated_at"] = datetime.now(timezone.utc)
                    break

                # Match existing logs where external_id was not stored,
                # but the provider ID exists inside provider_response.
                provider_response = log.get("provider_response") or {}
                recipients = provider_response.get("recipients") or []

                for recipient in recipients:
                    if recipient.get("id") == message_id:
                        log["status"] = new_status
                        log["external_id"] = message_id
                        log["updated_at"] = datetime.now(timezone.utc)
                        break
                else:
                    continue

                break

        return {"status": "processed"}


_sms_service_instance: Optional[SMSService] = None

def get_sms_service() -> SMSService:
    global _sms_service_instance
    if _sms_service_instance is None:
        _sms_service_instance = SMSService()
    return _sms_service_instance