import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from sqlalchemy.orm import Session

from database import SessionLocal

from ivhuRedu.models import User, UserType

from ivhuRedu.routers import auth as auth_router
from ivhuRedu.routers import user as user_router
from ivhuRedu.routers import (
    extension_worker as extension_worker_router,
)
from ivhuRedu.routers import farmer as farmer_router

from ivhuRedu.services.security import hash_password




load_dotenv()




logger = logging.getLogger("uvicorn.error")




limiter = Limiter(
    key_func=get_remote_address,
)



app = FastAPI(
    title="IvhuRedu API",
    version="1",
)



allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "",
).split(",")

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
        "X-Device-ID",
        "X-Platform",
    ],
)




app.include_router(
    auth_router.router
)

app.include_router(
    user_router.router
)

app.include_router(
    extension_worker_router.router
)

app.include_router(
    farmer_router.router
)




def onboard_default_admin() -> None:

    admin_phone = os.getenv(
        "ADMIN_PHONE_NUMBER"
    )

    admin_password = os.getenv(
        "ADMIN_PASSWORD"
    )

    if not admin_phone or not admin_password:

        logger.warning(
            "ADMIN_PHONE_NUMBER or ADMIN_PASSWORD not set. "
            "Skipping administrator creation."
        )

        return

    db: Session = SessionLocal()

    try:

        existing_admin = (
            db.query(User)
            .filter(
                User.user_type == UserType.ADMIN
            )
            .first()
        )

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

            email=os.getenv(
                "ADMIN_EMAIL"
            ),

            phone_number=admin_phone,

            hashed_password=hash_password(
                admin_password
            ),

            user_type=UserType.ADMIN,

            must_change_password=False,
        )

        db.add(admin)

        db.commit()

        logger.info(
            "Default administrator account created."
        )

    finally:

        db.close()




@app.on_event("startup")
def on_startup():

    onboard_default_admin()




@app.get("/health")
def health_check():

    return {
        "status": "ok"
    }