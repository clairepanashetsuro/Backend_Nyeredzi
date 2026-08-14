from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from ivhuRedu.schemas.sms import (
    SMSSendRequest, AlertSendRequest,
    OTPSendRequest, OTPVerifyRequest, OTPVerifyResponse,
    SMSLogsResponse, SMSPatchRequest,
    SMSDeleteResponse, SMSPatchResponse,
    SMSHistoryResponse, SMSSummaryResponse,
    SMSCallbackPayload,
)
from ivhuRedu.services.sms_service import SMSService

router = APIRouter(prefix="/sms", tags=["SMS"])


def get_sms_service():
    return SMSService()


@router.post("/send")
async def send_sms(request: SMSSendRequest, http_request: Request, service: SMSService = Depends(get_sms_service)):
    return service.send_sms(request, http_request)


@router.post("/alert")
async def send_alert(request: AlertSendRequest, http_request: Request, service: SMSService = Depends(get_sms_service)):
    return service.send_alert(request, http_request)


@router.post("/otp/send")
async def send_otp(request: OTPSendRequest, http_request: Request, service: SMSService = Depends(get_sms_service)):
    return service.send_otp(request, http_request)


@router.post("/otp/verify", response_model=OTPVerifyResponse)
async def verify_otp(request: OTPVerifyRequest, http_request: Request, service: SMSService = Depends(get_sms_service)):
    return service.verify_otp(request, http_request)


@router.get("/logs", response_model=SMSLogsResponse)
async def get_sms_logs(
    status: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    sender_id: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None),
    older_than_days: Optional[int] = Query(None),
    page: int = Query(1),
    page_size: int = Query(50),
    service: SMSService = Depends(get_sms_service),
):
    return service.get_logs(
        status=status,
        message_type=message_type,
        phone_number=phone_number,
        sender_id=sender_id,
        ip_address=ip_address,
        older_than_days=older_than_days,
        page=page,
        page_size=page_size,
    )


@router.get("/history", response_model=SMSHistoryResponse)
async def get_sms_history(limit: int = Query(100), service: SMSService = Depends(get_sms_service)):
    return service.get_history(limit)


@router.get("/summary", response_model=SMSSummaryResponse)
async def get_sms_summary(service: SMSService = Depends(get_sms_service)):
    return service.get_summary()


@router.post("/callback")
async def sms_callback(request: Request, payload: SMSCallbackPayload, service: SMSService = Depends(get_sms_service)):
    provided_secret = request.headers.get("X-Callback-Secret") or request.query_params.get("secret")
    return service.handle_callback(payload.model_dump(), provided_secret)


@router.patch("/logs", response_model=SMSPatchResponse)
async def patch_sms_logs(
    patch_data: SMSPatchRequest,
    status: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    sender_id: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None),
    older_than_days: Optional[int] = Query(None),
    service: SMSService = Depends(get_sms_service),
):
    return service.patch_logs(
        patch_data=patch_data.model_dump(exclude_unset=True),
        status=status,
        message_type=message_type,
        phone_number=phone_number,
        sender_id=sender_id,
        ip_address=ip_address,
        older_than_days=older_than_days,
    )


@router.delete("/logs", response_model=SMSDeleteResponse)
async def delete_sms_logs(
    status: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    sender_id: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None),
    older_than_days: Optional[int] = Query(None),
    service: SMSService = Depends(get_sms_service),
):
    return service.delete_logs(
        status=status,
        message_type=message_type,
        phone_number=phone_number,
        sender_id=sender_id,
        ip_address=ip_address,
        older_than_days=older_than_days,
    )