import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from sqlalchemy import select

from database import Base, engine, async_session

from ivhuRedu.models.user import User, UserType
from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.extension_worker import ExtensionWorker
from ivhuRedu.models.farmer_request import FarmerRequest
from ivhuRedu.models.field_report import FieldReport
from ivhuRedu.models.field_image import FieldImage
from ivhuRedu.models.location import Location

from ivhuRedu.services.security import hash_password

from ivhuRedu.routers.field_report import router as field_report_router
from ivhuRedu.routers.field_image import router as field_image_router
from ivhuRedu.routers.farmer_request import router as farmer_request_router
from ivhuRedu.routers.ussd import router as ussd_router
from ivhuRedu.routers import auth as auth_router
from ivhuRedu.routers import user as user_router
from ivhuRedu.routers import extension_worker as extension_worker_router
from ivhuRedu.routers import farmer as farmer_router
from ivhuRedu.routers.location import router as location_router
from ivhuRedu.routers.sms import router as sms_router

load_dotenv()
logger = logging.getLogger("uvicorn.error")

async def onboard_default_admin() -> None:
    admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_phone or not admin_password:
        logger.warning("ADMIN_PHONE_NUMBER or ADMIN_PASSWORD not set. Skipping administrator creation.")
        return
    async with async_session() as db:
        result = await db.execute(select(User).where(User.user_type == UserType.ADMIN))
        existing_admin = result.scalar_one_or_none()
        if existing_admin:
            return
        hashed_admin_password = await hash_password(admin_password)
        admin = User(
            first_name=os.getenv("ADMIN_FIRST_NAME", "System"),
            last_name=os.getenv("ADMIN_LAST_NAME", "Administrator"),
            email=os.getenv("ADMIN_EMAIL"),
            phone_number=admin_phone,
            hashed_password=hashed_admin_password,
            user_type=UserType.ADMIN,
            must_change_password=False,
        )
        db.add(admin)
        await db.commit()
        logger.info("Default administrator account created.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await onboard_default_admin()
    yield

app = FastAPI(
    title="IvhuRedu Agricultural Platform API",
    version="1.0.0",
    lifespan=lifespan
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts="*",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins != [""] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router.router, prefix="/users", tags=["Users"])
app.include_router(farmer_router.router, prefix="/farmers", tags=["Farmers"])
app.include_router(extension_worker_router.router, prefix="/extension-workers", tags=["Extension Workers"])
app.include_router(location_router, prefix="/locations", tags=["Locations"])
app.include_router(farmer_request_router, prefix="/farmer-requests", tags=["Farmer Requests"])
app.include_router(field_image_router, prefix="/field-images", tags=["Field Images"])
app.include_router(field_report_router, prefix="/field-reports", tags=["Field Reports"])
app.include_router(sms_router, prefix="/sms", tags=["SMS Broadcasts"])
app.include_router(ussd_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the IvhuRedu API", "status": "ok"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
