from fastapi import APIRouter, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession

from dependency import get_db

from ivhuRedu.services.ussd import USSDService


router = APIRouter(
    prefix="/ussd",
    tags=["USSD"],
)


@router.post("")
async def ussd_callback(
    sessionId: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    serviceCode: str = Form(""),
    networkCode: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    service = USSDService(db)

    return await service.handle(
        session_id=sessionId,
        phone_number=phoneNumber,
        text=text,
    )