from fastapi import APIRouter, Form, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ivhuRedu.routers.auth import router as auth_router

from database import get_db
from ivhuRedu.services.ussd import USSDService

router = APIRouter(tags=["USSD"])


@router.post("/callback", response_class=PlainTextResponse)
async def ussd_callback(
    session_id: str = Form(..., alias="sessionId"),
    phone_number: str = Form(..., alias="phoneNumber"),
    text: str = Form(default=""),
    service_code: str = Form(default="", alias="serviceCode"),
    network_code: str = Form(default="", alias="networkCode"),
    db: AsyncSession = Depends(get_db),
):
    phone_number = phone_number.strip()  
    print(f"[USSD CALLBACK] cleaned phoneNumber={phone_number!r} len={len(phone_number)}")
    service = USSDService(db)
    return await service.handle(session_id, phone_number, text)