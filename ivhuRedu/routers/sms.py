from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException

from ivhuRedu.schemas.sms import (
    SMSSendRequest, AlertSendRequest, OTPSendRequest, OTPVerifyRequest,
    OTPVerifyResponse, SMSPatchRequest, SMSDeleteResponse, SMSPatchResponse,
    SMSLogsResponse, SMSHistoryResponse, SMSSummaryResponse, SMSCallbackPayload,
)
from ivhuRedu.services.sms_services import SMSService

router = APIRouter(prefix="/sms", tags=["SMS"])

_sms_service_instance: Optional[SMSService] = None

def get_sms_service() -> SMSService:
    global _sms_service_instance
    if _sms_service_instance is None:
        _sms_service_instance = SMSService()
    return _sms_service_instance

class SMSLogFilters:
    def __init__(
        self,
        status: Optional[str] = Query(None),
        message_type: Optional[str] = Query(None),
        phone_number: Optional[str] = Query(None),
        sender_id: Optional[str] = Query(None),
        ip_address: Optional[str] = Query(None),
        older_than_days: Optional[int] = Query(None),
    ):
        self.status = status
        self.message_type = message_type
        self.phone_number = phone_number
        self.sender_id = sender_id
        self.ip_address = ip_address
        self.older_than_days = older_than_days


@router.post("/send")
async def send_sms(
    request: SMSSendRequest,
    http_request: Request,
    service: SMSService = Depends(get_sms_service),
):
    return await service.send_sms(request, http_request)


@router.post("/alert")
async def send_alert(
    request: AlertSendRequest,
    http_request: Request,
    service: SMSService = Depends(get_sms_service),
):
    return await service.send_alert(request, http_request)


@router.post("/otp/send")
async def send_otp(
    request: OTPSendRequest,
    http_request: Request,
    service: SMSService = Depends(get_sms_service),
):
    return await service.send_otp(request, http_request)


@router.post("/otp/verify", response_model=OTPVerifyResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    http_request: Request,
    service: SMSService = Depends(get_sms_service),
):
    return await service.verify_otp(request, http_request)


@router.get("/logs", response_model=SMSLogsResponse)
async def get_sms_logs(
    filters: SMSLogFilters = Depends(),
    service: SMSService = Depends(get_sms_service),
):
    return await service.get_logs(
        status=filters.status,
        message_type=filters.message_type,
        phone_number=filters.phone_number,
        sender_id=filters.sender_id,
        ip_address=filters.ip_address,
        older_than_days=filters.older_than_days,
    )


@router.get("/history", response_model=SMSHistoryResponse)
async def get_sms_history(
    limit: int = Query(100, ge=1, le=1000),
    service: SMSService = Depends(get_sms_service),
):
    return await service.get_history(limit)


@router.get("/summary", response_model=SMSSummaryResponse)
async def get_sms_summary(
    service: SMSService = Depends(get_sms_service),
):
    return await service.get_summary()


@router.post("/callback")
async def sms_callback(
    request: Request,
    payload: SMSCallbackPayload,
    service: SMSService = Depends(get_sms_service),
):
    secret = request.query_params.get("secret")
    if not secret:
        raise HTTPException(status_code=401, detail="Missing webhook secret query parameter")

    return await service.handle_callback(payload.model_dump(), secret)


@router.patch("/logs", response_model=SMSPatchResponse)
async def patch_logs(
    patch_data: SMSPatchRequest,
    filters: SMSLogFilters = Depends(),
    service: SMSService = Depends(get_sms_service),
):
    return await service.patch_logs(
        patch_data=patch_data.model_dump(exclude_unset=True),
        status=filters.status,
        message_type=filters.message_type,
        phone_number=filters.phone_number,
        sender_id=filters.sender_id,
        ip_address=filters.ip_address,
        older_than_days=filters.older_than_days,
    )


@router.delete("/logs", response_model=SMSDeleteResponse)
async def delete_sms_logs(
    filters: SMSLogFilters = Depends(),
    service: SMSService = Depends(get_sms_service),
):
    return await service.delete_logs(
        status=filters.status,
        message_type=filters.message_type,
        phone_number=filters.phone_number,
        sender_id=filters.sender_id,
        ip_address=filters.ip_address,
        older_than_days=filters.older_than_days,
    )