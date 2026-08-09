from fastapi import FastAPI
from database import Base, engine 

from ivhuRedu.models.farmer_request import FarmerRequest
from ivhuRedu.models.location import Location
from ivhuRedu.models.user import User

from ivhuRedu.routers.farmer_request import router as farmer_request_router

try:
    Base.metadata.create_all(bind=engine)
    print("Database synchronized successfully.")
except Exception as e:
    print(f"Notice: Table creation skipped due to uninitialized peer schemas: {e}")

app = FastAPI(title="IvhuRedu API", version="1.0.0")

app.include_router(farmer_request_router, prefix="/farmer-requests", tags=["Farmer Requests"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the IvhuRedu API"}