import os
import secrets
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException

logger = logging.getLogger("uvicorn.error")


class SMSService:
    def __init__(self):
        self.api_key = os.getenv("SMS_LEOPARD_API_KEY")
        self.api_secret = os.getenv("SMS_LEOPARD_API_SECRET")
        self.sender_id = os.getenv("SMS_LEOPARD_SENDER_ID") or "IvhuRedu"
        self.callback_secret = os.getenv("SMS_CALLBACK_SECRET") or "my_super_secret_webhook_token_123"
        self.url = os.getenv("SMS_LEOPARD_API_URL") or "https://api.smsleopard.com/v1/sms/send"
        self.status_url = os.getenv("SMS_STATUS_CALLBACK_URL")
        self.otp_store: Dict[str, Dict[str, Any]] = {}
        self.logs: Dict[str, Dict[str, Any]] = {}

    async def _send(self, destination: Any, message: str, sender_id: Optional[str]) -> Dict[str, Any]:
        if not self.api_key or not self.api_secret or "your_actual" in self.api_key.lower():
            logger.info(f"[MOCK MODE] Simulating SMS dispatch to: {destination}")
            return {"status": "success", "message_id": f"mock_{uuid.uuid4().hex[:8]}"}

        payload: Dict[str, Any] = {
            "source": sender_id or self.sender_id,
            "message": message,
            "destination": destination if isinstance(destination, list) else [{"number": destination}],
        }

        if self.status_url:
            payload["status_url"] = self.status_url
            payload["status_secret"] = self.callback_secret

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(
                    self.url,
                    auth=(self.api_key, self.api_secret),
                    json=payload,
                )
                response.raise_for_status()
                try:
                    return response.json()
                except Exception:
                    return {"status": "success", "raw_response": response.text}
            except httpx.HTTPStatusError as exc:
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

    def _filter(
        self,
        status=None,
        message_type=None,
        phone_number=None,
        sender_id=None,
        ip_address=None,
        older_than_days=None,
    ):
        results = []
        for log in self.logs.values():
            if status and status.lower() not in log.get("status", "").lower():
                continue
            if message_type and message_type.lower() not in log.get("type", "").lower():
                continue
            if phone_number and phone_number not in log.get("recipients", ""):
                continue
            if sender_id and sender_id.lower() not in str(log.get("sender_id", "")).lower():
                continue
            if ip_address and ip_address != log.get("ip"):
                continue
            if older_than_days is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
                if log.get("created_at") and log["created_at"] > cutoff:
                    continue
            results.append(log)
        return results

    async def send_sms(self, request: Any, http_request: Optional[Any] = None) -> Dict[str, Any]:
        resp = await self._send(request.phone_number, request.message, request.sender_id)
        log_id = self._log({
            "type": "sms",
            "recipients": request.phone_number,
            "message": request.message,
            "status": "sent",
            "sender_id": request.sender_id or self.sender_id,
            "ip": self._ip(http_request),
            "provider_response": resp,
            "external_id": resp.get("message_id") or resp.get("id"),
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
            "external_id": resp.get("message_id") or resp.get("id"),
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

        # ADD THIS LINE RIGHT HERE ↓↓↓
        print(f"\n*** OTP FOR {request.phone_number}: {otp} ***\n")

        self.otp_store[request.phone_number] = {
            "otp": otp,
            "expires_at": expires,
        }

        message = f"Your OTP code is {otp}. It expires in 5 minutes."
        resp = await self._send(request.phone_number, message, request.sender_id)

        log_id = self._log({
            "type": "otp",
            "recipients": request.phone_number,
            "message": message,
            "status": "sent",
            "sender_id": request.sender_id or self.sender_id,
            "ip": self._ip(http_request),
            "provider_response": resp,
            "external_id": resp.get("message_id") or resp.get("id"),
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

    async def get_logs(
        self,
        status,
        message_type,
        phone_number,
        sender_id,
        ip_address,
        older_than_days,
    ) -> Dict[str, Any]:
        logs = self._filter(status, message_type, phone_number, sender_id, ip_address, older_than_days)
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

    async def delete_logs(
        self,
        status,
        message_type,
        phone_number,
        sender_id,
        ip_address,
        older_than_days,
    ) -> Dict[str, Any]:
        if not any([status, message_type, phone_number, sender_id, ip_address, older_than_days is not None]):
            raise HTTPException(
                status_code=400,
                detail="At least one filter parameter is required for deletion",
            )

        to_del = [
            log["id"]
            for log in self._filter(status, message_type, phone_number, sender_id, ip_address, older_than_days)
        ]
        for lid in to_del:
            del self.logs[lid]

        return {"success": True, "deleted_count": len(to_del)}

    async def patch_logs(
        self,
        patch_data: dict,
        status,
        message_type,
        phone_number,
        sender_id,
        ip_address,
        older_than_days,
    ) -> Dict[str, Any]:
        updated = 0
        for log in self._filter(status, message_type, phone_number, sender_id, ip_address, older_than_days):
            if "status" in patch_data and patch_data["status"] is not None:
                log["status"] = patch_data["status"]
                log["updated_at"] = datetime.now(timezone.utc)
                updated += 1
        return {"success": True, "updated_count": updated}

    async def get_history(self, limit: int) -> Dict[str, Any]:
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

    async def handle_callback(self, payload: dict, provided_secret: Optional[str]) -> Dict[str, Any]:
        if not provided_secret or not secrets.compare_digest(provided_secret, self.callback_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

        message_id = payload.get("message_id")
        if message_id:
            for log in self.logs.values():
                if log.get("external_id") == message_id:
                    log["status"] = payload.get("status", "unknown")
                    log["updated_at"] = datetime.now(timezone.utc)
                    break

        return {"status": "processed"}