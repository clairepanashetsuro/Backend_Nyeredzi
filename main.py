import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ivhuRedu.routers.sms import router as sms_router

app = FastAPI(
    title="IvhuRedu SMS & OTP Gateway",
    version="1.0.0",
    docs_url="/docs" if os.getenv("APP_ENV") == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(sms_router)

try:
    from ivhuRedu.routers.location import router as location_router
    app.include_router(location_router)
except ImportError:
    pass

try:
    from ivhuRedu.routers.user import router as user_router
    app.include_router(user_router)
except ImportError:
    pass

try:
    from ivhuRedu.routers.field_report import router as field_report_router
    app.include_router(field_report_router)
except ImportError:
    pass

try:
    from ivhuRedu.routers.field_image import router as field_image_router
    app.include_router(field_image_router)
except ImportError:
    pass


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "sms-otp-gateway"}