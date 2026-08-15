from fastapi import APIRouter, Depends, Request

from ivhuRedu.schemas.sms import (
    SMSSendRequest,
    AlertSendRequest,
    OTPSendRequest,
    OTPVerifyRequest,
    SMSPatchRequest,
    SMSLogFilters,
    SMSCallbackPayload,
)
from ivhuRedu.services.sms_services import SMSService, get_sms_service

router = APIRouter(prefix="/sms", tags=["SMS"])


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


@router.post("/otp/verify")
async def verify_otp(
    request: OTPVerifyRequest,
    http_request: Request,
    service: SMSService = Depends(get_sms_service),
):
    return await service.verify_otp(request, http_request)


@router.get("/logs")
async def get_sms_logs(
    filters: SMSLogFilters = Depends(),
    service: SMSService = Depends(get_sms_service),
):
    return await service.get_logs(filters)


@router.get("/history")
async def get_sms_history(
    limit: int = 100,
    service: SMSService = Depends(get_sms_service),
):
    return await service.get_history(limit)


@router.get("/summary")
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
    return await service.handle_callback(payload, request)


@router.patch("/logs")
async def patch_logs(
    patch_data: SMSPatchRequest,
    filters: SMSLogFilters = Depends(),
    service: SMSService = Depends(get_sms_service),
):
    return await service.patch_logs(patch_data, filters)


@router.delete("/logs")
async def delete_sms_logs(
    filters: SMSLogFilters = Depends(),
    service: SMSService = Depends(get_sms_service),
):
    return await service.delete_logs(filters)