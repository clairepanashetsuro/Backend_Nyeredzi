import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from database import async_session, engine, Base

from ivhuRedu.models import User, UserType
from ivhuRedu.models.farmer_request import FarmerRequest

from ivhuRedu.routers.farmer_request import router as farmer_request_router
from ivhuRedu.routers.ussd import router as ussd_router

from ivhuRedu.services.security import hash_password

load_dotenv()

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="IvhuRedu API",
    version="1",
)

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "",
).split(",")

app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts="*",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)

app.include_router(farmer_request_router, prefix="/farmer-requests", tags=["Farmer Requests"])
app.include_router(ussd_router, prefix="/ussd", tags=["USSD"])


@app.get("/")
def read_root():
    return {"message": "Welcome to the IvhuRedu API", "status": "ok"}


async def onboard_default_admin() -> None:
    admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_phone or not admin_password:
        logger.warning(
            "ADMIN_PHONE_NUMBER or ADMIN_PASSWORD not set. "
            "Skipping administrator creation."
        )
        return

    async with async_session() as db:
        result = await db.execute(
            select(User).where(
                User.user_type == UserType.ADMIN
            )
        )

        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            return

        admin = User(
            first_name=os.getenv(
                "ADMIN_FIRST_NAME",
                "System",
            ),
            last_name=os.getenv(
                "ADMIN_LAST_NAME",
                "Administrator",
            ),
            email=os.getenv("ADMIN_EMAIL"),
            phone_number=admin_phone,
            hashed_password=hash_password(admin_password),
            user_type=UserType.ADMIN,
            must_change_password=False,
        )

        db.add(admin)
        await db.commit()
        logger.info("Default administrator account created.")


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            print("Database synchronized successfully.")
        except Exception as e:
            print(f"Notice: Table creation skipped due to uninitialized peer schemas: {e}")
    await onboard_default_admin()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
    }
