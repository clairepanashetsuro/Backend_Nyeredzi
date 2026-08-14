import os
import base64
import uuid
import random
import string
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from collections import defaultdict
from fastapi import HTTPException

from ivhuRedu.schemas.sms import (
    MessageType, MessageStatus,
    SMSSendRequest, AlertSendRequest,
    OTPSendRequest, OTPVerifyRequest,
    SMSLogEntry, SMSDeleteResponse, SMSPatchResponse
)


SMS_LEOPARD_BASE_URL = os.getenv("SMS_LEOPARD_BASE_URL", "https://api.smsleopard.com/v1")
SMS_LEOPARD_API_KEY = os.getenv("SMS_LEOPARD_API_KEY")
SMS_LEOPARD_API_SECRET = os.getenv("SMS_LEOPARD_API_SECRET")
SMS_LEOPARD_SENDER_ID = os.getenv("SMS_LEOPARD_SENDER_ID")
SMS_CALLBACK_SECRET = os.getenv("SMS_CALLBACK_SECRET")

OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))
OTP_COOLDOWN_SECONDS = int(os.getenv("OTP_COOLDOWN_SECONDS", "60"))
OTP_HOURLY_MAX = int(os.getenv("OTP_HOURLY_MAX", "10"))


def _get_basic_auth_header():
    credentials = f"{SMS_LEOPARD_API_KEY}:{SMS_LEOPARD_API_SECRET}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded}"


def _get_headers():
    return {
        "Authorization": _get_basic_auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


class SMSLogStore:
    def __init__(self):
        self._logs = {}
        self._otp_store = {}

    def add(self, entry):
        log_id = str(uuid.uuid4())
        entry["id"] = log_id
        entry["created_at"] = datetime.now(timezone.utc)
        entry.setdefault("updated_at", None)
        self._logs[log_id] = entry
        return log_id

    def get(self, log_id):
        return self._logs.get(log_id)

    def get_all(self):
        return list(self._logs.values())

    def delete(self, log_id):
        if log_id in self._logs:
            del self._logs[log_id]
            return True
        return False

    def delete_many(self, log_ids):
        count = 0
        for lid in log_ids:
            if self.delete(lid):
                count += 1
        return count

    def update(self, log_id, data):
        if log_id in self._logs:
            self._logs[log_id].update(data)
            self._logs[log_id]["updated_at"] = datetime.now(timezone.utc)
            return True
        return False

    def store_otp(self, phone, code, expires, log_id):
        self._otp_store[phone] = {
            "code": code,
            "expires_at": expires,
            "log_id": log_id,
            "verified": False,
        }

    def get_otp(self, phone):
        return self._otp_store.get(phone)

    def clear_otp(self, phone):
        self._otp_store.pop(phone, None)


_store = SMSLogStore()


class SMSLeopardClient:
    @staticmethod
    def _check_credentials():
        if not SMS_LEOPARD_API_KEY or not SMS_LEOPARD_API_SECRET:
            raise HTTPException(status_code=503, detail="SMS Leopard credentials not configured")

    @staticmethod
    def send_single(message, recipients, sender_id, status_url=None, status_secret=None):
        SMSLeopardClient._check_credentials()
        destination = [{"number": r} for r in recipients]
        payload = {
            "message": message,
            "destination": destination,
        }
        if sender_id:
            payload["source"] = sender_id
        if status_url:
            payload["status_url"] = status_url
            payload["status_secret"] = status_secret or SMS_CALLBACK_SECRET
        url = f"{SMS_LEOPARD_BASE_URL}/sms/send"
        resp = requests.post(url, headers=_get_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def send_customized(destinations, sender_id, template, status_url=None, status_secret=None):
        SMSLeopardClient._check_credentials()
        payload = {
            "multi": True,
            "message": template,
            "destination": destinations,
        }
        if sender_id:
            payload["source"] = sender_id
        if status_url:
            payload["status_url"] = status_url
            payload["status_secret"] = status_secret or SMS_CALLBACK_SECRET
        url = f"{SMS_LEOPARD_BASE_URL}/sms/send"
        resp = requests.post(url, headers=_get_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()


class SMSService:
    def __init__(self):
        self.store = _store
        self.leopard = SMSLeopardClient()
        self._otp_attempts = defaultdict(int)
        self._otp_send_times = {}
        self._otp_hourly_counts = defaultdict(list)

    def _normalize_phone(self, phone):
        phone = str(phone).strip().replace(" ", "").replace("-", "").replace("+", "")
        if not phone.isdigit() or len(phone) < 9:
            raise HTTPException(status_code=400, detail="Invalid phone number format")
        return phone

    def _validate_phones(self, phones):
        return [self._normalize_phone(p) for p in phones]

    def _validate_message(self, message):
        if not message or len(message.strip()) == 0:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        if len(message) > 1600:
            raise HTTPException(status_code=400, detail="Message exceeds 1600 characters")
        return message.strip()

    def _validate_otp_length(self, length):
        if length is None:
            return OTP_LENGTH
        if not isinstance(length, int) or length < 4 or length > 8:
            raise HTTPException(status_code=400, detail="OTP length must be between 4 and 8")
        return length

    def _validate_expiry_minutes(self, minutes):
        if minutes is None:
            return OTP_TTL_SECONDS // 60
        if not isinstance(minutes, int) or minutes < 1 or minutes > 30:
            raise HTTPException(status_code=400, detail="Expiry minutes must be between 1 and 30")
        return minutes

    def _validate_page(self, page):
        if page is None:
            return 1
        if not isinstance(page, int) or page < 1:
            raise HTTPException(status_code=400, detail="Page must be a positive integer")
        return page

    def _validate_page_size(self, page_size):
        if page_size is None:
            return 50
        if not isinstance(page_size, int) or page_size < 1 or page_size > 200:
            raise HTTPException(status_code=400, detail="Page size must be between 1 and 200")
        return page_size

    def _validate_limit(self, limit):
        if limit is None:
            return 100
        if not isinstance(limit, int) or limit < 1 or limit > 500:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 500")
        return limit

    def _mask_phone(self, phone):
        if len(phone) <= 4:
            return "****"
        return phone[:2] + "****" + phone[-2:]

    def _generate_otp(self, length):
        return "".join(random.choices(string.digits, k=length))

    def _enforce_otp_rate_limits(self, phone: str):
        now = datetime.now(timezone.utc)
        last_send = self._otp_send_times.get(phone)
        if last_send:
            elapsed = (now - last_send).total_seconds()
            if elapsed < OTP_COOLDOWN_SECONDS:
                wait = int(OTP_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(status_code=429, detail=f"Please wait {wait} seconds before requesting another OTP.")
        hour_ago = now - timedelta(hours=1)
        self._otp_hourly_counts[phone] = [t for t in self._otp_hourly_counts[phone] if t > hour_ago]
        if len(self._otp_hourly_counts[phone]) >= OTP_HOURLY_MAX:
            raise HTTPException(status_code=429, detail=f"Maximum {OTP_HOURLY_MAX} OTP requests per hour exceeded. Try again later.")

    def _check_otp_attempts(self, phone: str):
        if self._otp_attempts[phone] >= OTP_MAX_ATTEMPTS:
            otp_data = self.store.get_otp(phone)
            if otp_data:
                self.store.update(otp_data["log_id"], {"status": MessageStatus.FAILED.value})
                self.store.clear_otp(phone)
            raise HTTPException(status_code=429, detail="Too many failed attempts. OTP invalidated. Request a new one.")

    def _record_otp_send(self, phone: str):
        now = datetime.now(timezone.utc)
        self._otp_send_times[phone] = now
        self._otp_hourly_counts[phone].append(now)
        self._otp_attempts[phone] = 0

    def _matches_filters(self, entry, filters):
        field_map = {
            "message_type": "type",
            "ip_address": "ip",
            "phone_number": "recipients",
            "status": "status",
            "sender_id": "sender_id",
        }
        for fk, fv in filters.items():
            if fk == "older_than_days":
                try:
                    days = int(fv)
                    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                    created = entry.get("created_at")
                    if created and isinstance(created, datetime):
                        if created > cutoff:
                            return False
                    continue
                except (ValueError, TypeError):
                    continue
            if fk == "phone_number":
                masked = self._mask_phone(fv)
                entry_recipients = entry.get("recipients", "")
                if fv not in entry_recipients and masked not in entry_recipients:
                    return False
                continue
            log_key = field_map.get(fk, fk)
            log_val = str(entry.get(log_key, "")).lower()
            filter_val = str(fv).lower()
            if filter_val and filter_val not in log_val:
                return False
        return True

    def _build_filters(self, status, message_type, phone_number, sender_id, ip_address, older_than_days):
        filters = {}
        if status:
            filters["status"] = status
        if message_type:
            filters["message_type"] = message_type
        if phone_number:
            filters["phone_number"] = self._normalize_phone(phone_number)
        if sender_id:
            filters["sender_id"] = sender_id
        if ip_address:
            filters["ip_address"] = ip_address
        if older_than_days is not None:
            filters["older_than_days"] = older_than_days
        return filters

    def send_sms(self, request, http_request=None):
        client_ip = http_request.client.host if http_request and http_request.client else None
        phone = self._normalize_phone(request.phone_number)
        message = self._validate_message(request.message)
        sender_id = request.sender_id or SMS_LEOPARD_SENDER_ID
        provider_resp = self.leopard.send_single(
            message=message,
            recipients=[phone],
            sender_id=sender_id,
        )
        log_entry = {
            "type": MessageType.SMS.value,
            "recipients": phone,
            "message": message,
            "status": MessageStatus.SENT.value,
            "sender_id": sender_id,
            "ip": client_ip,
            "provider_response": provider_resp,
            "external_id": provider_resp.get("message_id") or provider_resp.get("id"),
        }
        log_id = self.store.add(log_entry)
        return {
            "success": True,
            "message": "SMS sent successfully",
            "log_id": log_id,
            "provider_response": provider_resp,
            "recipient": phone,
        }

    def send_alert(self, request, http_request=None):
        client_ip = http_request.client.host if http_request and http_request.client else None
        phones = self._validate_phones(request.phone_numbers)
        message = self._validate_message(request.message)
        sender_id = request.sender_id or SMS_LEOPARD_SENDER_ID
        destinations = [{"number": p, "message": message} for p in phones]
        provider_resp = self.leopard.send_customized(
            destinations=destinations,
            sender_id=sender_id,
            template=message,
        )
        log_entry = {
            "type": MessageType.ALERT.value,
            "recipients": ",".join(phones),
            "message": message,
            "status": MessageStatus.SENT.value,
            "sender_id": sender_id,
            "ip": client_ip,
            "provider_response": provider_resp,
            "external_id": provider_resp.get("message_id") or provider_resp.get("id"),
        }
        log_id = self.store.add(log_entry)
        return {
            "success": True,
            "message": f"Alert sent to {len(phones)} recipient(s)",
            "log_id": log_id,
            "recipients_count": len(phones),
            "provider_response": provider_resp,
        }

    def send_otp(self, request, http_request=None):
        client_ip = http_request.client.host if http_request and http_request.client else None
        phone = self._normalize_phone(request.phone_number)
        self._enforce_otp_rate_limits(phone)
        otp_length = self._validate_otp_length(request.otp_length)
        expiry_minutes = self._validate_expiry_minutes(request.expiry_minutes)
        sender_id = request.sender_id or SMS_LEOPARD_SENDER_ID
        existing = self.store.get_otp(phone)
        if existing:
            self.store.update(existing["log_id"], {"status": MessageStatus.EXPIRED.value})
            self.store.clear_otp(phone)
        otp_code = self._generate_otp(otp_length)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        message = f"Your Nyeredzi verification code is: {otp_code}. Valid for {expiry_minutes} minutes. Do not share this code."
        provider_resp = self.leopard.send_single(
            message=message,
            recipients=[phone],
            sender_id=sender_id,
        )
        log_entry = {
            "type": MessageType.OTP_LOGIN.value,
            "recipients": phone,
            "message": message.replace(otp_code, "******"),
            "status": MessageStatus.PENDING.value,
            "sender_id": sender_id,
            "ip": client_ip,
            "otp_code": otp_code,
            "otp_expires_at": expires_at,
            "provider_response": provider_resp,
            "external_id": provider_resp.get("message_id") or provider_resp.get("id"),
        }
        log_id = self.store.add(log_entry)
        self.store.store_otp(phone, otp_code, expires_at, log_id)
        self._record_otp_send(phone)
        return {
            "success": True,
            "message": "OTP sent successfully",
            "log_id": log_id,
            "otp_expires_at": expires_at.isoformat(),
            "phone_number": phone,
            "otp_length": otp_length,
            "expiry_minutes": expiry_minutes,
        }

    def verify_otp(self, request, http_request=None):
        phone = self._normalize_phone(request.phone_number)
        otp_data = self.store.get_otp(phone)
        if not otp_data:
            raise HTTPException(status_code=400, detail="No active OTP found for this phone number")
        self._check_otp_attempts(phone)
        if datetime.now(timezone.utc) > otp_data["expires_at"]:
            self.store.update(otp_data["log_id"], {"status": MessageStatus.EXPIRED.value})
            self.store.clear_otp(phone)
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
        if otp_data["code"] != request.otp_code:
            self._otp_attempts[phone] += 1
            remaining = OTP_MAX_ATTEMPTS - self._otp_attempts[phone]
            raise HTTPException(status_code=400, detail=f"Invalid OTP code. {remaining} attempt(s) remaining.")
        self.store.update(otp_data["log_id"], {"status": MessageStatus.DELIVERED.value})
        self.store.clear_otp(phone)
        self._otp_attempts[phone] = 0
        return {
            "success": True,
            "message": "OTP verified successfully",
            "phone_number": phone,
        }

    def get_logs(self, status, message_type, phone_number, sender_id, ip_address, older_than_days, page, page_size):
        page = self._validate_page(page)
        page_size = self._validate_page_size(page_size)
        filters = self._build_filters(status, message_type, phone_number, sender_id, ip_address, older_than_days)
        all_logs = self.store.get_all()
        matched = [log for log in all_logs if self._matches_filters(log, filters)]
        matched.sort(key=lambda x: x.get("created_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        total = len(matched)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = matched[start:end]
        return {
            "logs": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def delete_logs(self, status, message_type, phone_number, sender_id, ip_address, older_than_days):
        filters = self._build_filters(status, message_type, phone_number, sender_id, ip_address, older_than_days)
        if not filters:
            raise HTTPException(
                status_code=400,
                detail="Deletion refused: at least one filter is required. Specify one of: status, message_type, phone_number, sender_id, ip_address, or older_than_days."
            )
        all_logs = self.store.get_all()
        to_delete = [log["id"] for log in all_logs if self._matches_filters(log, filters)]
        deleted_count = self.store.delete_many(to_delete)
        for log_id in to_delete:
            for phone, otp_data in list(self.store._otp_store.items()):
                if otp_data.get("log_id") == log_id:
                    self.store.clear_otp(phone)
        return SMSDeleteResponse(
            deleted=deleted_count,
            message=f"Successfully deleted {deleted_count} log(s)",
            filters_applied=filters,
        )

    def patch_logs(self, patch_data, status, message_type, phone_number, sender_id, ip_address, older_than_days):
        filters = self._build_filters(status, message_type, phone_number, sender_id, ip_address, older_than_days)
        all_logs = self.store.get_all()
        to_update = [log["id"] for log in all_logs if self._matches_filters(log, filters)]
        update_payload = {}
        if "status" in patch_data:
            update_payload["status"] = patch_data["status"]
        updated_count = 0
        for log_id in to_update:
            if self.store.update(log_id, update_payload):
                updated_count += 1
        return SMSPatchResponse(
            updated=updated_count,
            message=f"Successfully updated {updated_count} log(s)",
            filters_applied=filters if filters else {},
        )

    def get_history(self, limit):
        limit = self._validate_limit(limit)
        all_logs = self.store.get_all()
        all_logs.sort(key=lambda x: x.get("created_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return {
            "history": all_logs[:limit],
            "total": len(all_logs),
        }

    def get_summary(self):
        all_logs = self.store.get_all()
        summary = {
            "total_sent": 0,
            "total_failed": 0,
            "total_pending": 0,
            "total_delivered": 0,
            "total_expired": 0,
            "total_otp": 0,
            "total_alerts": 0,
            "total_sms": 0,
        }
        for log in all_logs:
            log_status = log.get("status", "").lower()
            log_type = log.get("type", "").lower()
            if log_status == MessageStatus.SENT.value:
                summary["total_sent"] += 1
            elif log_status == MessageStatus.FAILED.value:
                summary["total_failed"] += 1
            elif log_status == MessageStatus.PENDING.value:
                summary["total_pending"] += 1
            elif log_status == MessageStatus.DELIVERED.value:
                summary["total_delivered"] += 1
            elif log_status == MessageStatus.EXPIRED.value:
                summary["total_expired"] += 1
            if log_type in (MessageType.OTP.value, MessageType.OTP_LOGIN.value):
                summary["total_otp"] += 1
            elif log_type == MessageType.ALERT.value:
                summary["total_alerts"] += 1
            elif log_type == MessageType.SMS.value:
                summary["total_sms"] += 1
        return summary

    def handle_callback(self, payload, provided_secret=None):
        if SMS_CALLBACK_SECRET and provided_secret != SMS_CALLBACK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid callback secret")
        message_id = payload.get("message_id")
        delivery_status = payload.get("status", "unknown")
        all_logs = self.store.get_all()
        for log in all_logs:
            if log.get("external_id") == message_id:
                status_map = {
                    "delivered": MessageStatus.DELIVERED.value,
                    "failed": MessageStatus.FAILED.value,
                    "sent": MessageStatus.SENT.value,
                    "pending": MessageStatus.PENDING.value,
                }
                new_status = status_map.get(delivery_status.lower(), MessageStatus.SENT.value)
                self.store.update(log["id"], {
                    "status": new_status,
                    "provider_response": {**log.get("provider_response", {}), "callback": payload},
                })
                return {"success": True, "message": "Callback processed", "log_id": log["id"]}
        return {"success": False, "message": "Message ID not found"}