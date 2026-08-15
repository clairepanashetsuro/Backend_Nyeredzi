import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from ivhuRedu.database import Base, engine, init_db 

from ivhuRedu.models.user import User
from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.extension_worker import ExtensionWorker
from ivhuRedu.models.farmer_request import FarmerRequest
from ivhuRedu.models.field_report import FieldReport
from ivhuRedu.models.location import Location

from ivhuRedu.routers.field_report import router as field_report_router
from ivhuRedu.routers.field_image import router as field_image_router
from ivhuRedu.routers import auth as auth_router
from ivhuRedu.routers import user as user_router
from ivhuRedu.routers import extension_worker as extension_worker_router
from ivhuRedu.routers import farmer as farmer_router
from ivhuRedu.routers.location import router as location_router

load_dotenv()
logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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

app.include_router(field_report_router)
app.include_router(field_image_router)

app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(extension_worker_router.router)
app.include_router(farmer_router.router)
app.include_router(location_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the IvhuRedu API", "status": "ok"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
