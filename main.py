from fastapi import FastAPI
from database import Base, engine
from dotenv import load_dotenv

from ivhuRedu.models.farmer_request import FarmerRequest
from ivhuRedu.models.user import User

from ivhuRedu.routers.farmer_request import router as farmer_request_router
from ivhuRedu.routers.ussd import router as ussd_router

from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

load_dotenv()

try:
    Base.metadata.create_all(bind=engine)
    print("Database synchronized successfully.")
except Exception as e:
    print(f"Notice: Table creation skipped due to uninitialized peer schemas: {e}")

app = FastAPI(title="IvhuRedu Agricultural Platform API", version="1.0.0")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(farmer_request_router, prefix="/farmer-requests", tags=["Farmer Requests"])
app.include_router(ussd_router, prefix="/ussd", tags=["USSD"])


@app.get("/")
def read_root():
    return {"message": "Welcome to the IvhuRedu API", "status": "ok"}