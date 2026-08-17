from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ivhuRedu.database import Base, engine
import asyncio

# Force load all database structures via the package init layout
import ivhuRedu.models

from ivhuRedu.routers.auth import router as auth_router
from ivhuRedu.routers.user import router as user_router
from ivhuRedu.routers.farmer import router as farmer_router
from ivhuRedu.routers.extension_worker import router as extension_worker_router
from ivhuRedu.routers.location import router as location_router
from ivhuRedu.routers.farmer_request import router as farmer_request_router
from ivhuRedu.routers.field_image import router as field_image_router
from ivhuRedu.routers.field_report import router as field_report_router
from ivhuRedu.routers.ussd import router as ussd_router

app = FastAPI(title="IvhuRedu Platform API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

async def init_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("startup")
async def on_startup():
    await init_tables()

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(farmer_router, prefix="/farmers", tags=["Farmers"])
app.include_router(extension_worker_router, prefix="/extension-workers", tags=["Extension Workers"])
app.include_router(location_router, prefix="/locations", tags=["Locations"])
app.include_router(farmer_request_router, prefix="/farmer-requests", tags=["Farmer Requests"])
app.include_router(field_image_router, prefix="/field-images", tags=["Field Images"])
app.include_router(field_report_router, prefix="/field-reports", tags=["Field Reports"])
app.include_router(ussd_router, prefix="/ussd", tags=["USSD"])

@app.get("/")
def read_root(): return {"status": "Active"}
