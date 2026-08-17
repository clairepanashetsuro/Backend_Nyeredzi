import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from database import async_session, engine, Base
from ivhuRedu.models import User, UserType

# Router Imports
from ivhuRedu.routers.auth import router as auth_router
from ivhuRedu.routers.user import router as user_router
from ivhuRedu.routers.extension_worker import router as extension_worker_router
from ivhuRedu.routers.farmer import router as farmer_router
from ivhuRedu.routers.location import router as location_router
from ivhuRedu.routers.farmer_request import router as farmer_request_router
from ivhuRedu.routers.ussd import router as ussd_router

try:
    from ivhuRedu.routers.sms_log import router as sms_log_router
except ImportError:
    from ivhuRedu.routers.sms import router as sms_log_router

from ivhuRedu.services.security import hash_password

load_dotenv()
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="IvhuRedu Agricultural Platform API", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins != [""] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cleaned Router Inclusions
app.include_router(auth_router, tags=["auth"])
app.include_router(user_router, tags=["users"])
app.include_router(extension_worker_router, tags=["extension-workers"])
app.include_router(farmer_router, tags=["farmers"])
app.include_router(location_router, tags=["Locations"])

# Re-added clean structural prefixes for bare endpoint modules
app.include_router(farmer_request_router, prefix="/farmer-requests", tags=["Farmer Requests"])

# FIX: Mount USSD and SMS without double tags or conflicting prefixes
app.include_router(ussd_router, prefix="/ussd", tags=["USSD"])
app.include_router(sms_log_router)

@app.get("/", tags=["System"])
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "message": "Welcome to the IvhuRedu API"}

async def onboard_default_admin() -> None:
    admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_phone or not admin_password:
        return
    async with async_session() as db:
        result = await db.execute(select(User).where(User.user_type == UserType.ADMIN))
        if result.scalar_one_or_none():
            return
        admin = User(
            first_name=os.getenv("ADMIN_FIRST_NAME", "System"),
            last_name=os.getenv("ADMIN_LAST_NAME", "Administrator"),
            phone_number=admin_phone,
            email=os.getenv("ADMIN_EMAIL"),
            hashed_password=hash_password(admin_password),
            user_type=UserType.ADMIN,
            must_change_password=False,
        )
        db.add(admin)
        await db.commit()

@app.on_event("startup")
async def on_startup():
    await onboard_default_admin()
