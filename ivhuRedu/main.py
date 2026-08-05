from fastapi import FastAPI
from ivhuRedu.database import Base, engine 
from ivhuRedu.models.farmer import Farmer
from ivhuRedu.models.extension_worker import ExtensionWorker
from ivhuRedu.models.farmer_request import FarmerRequest
from ivhuRedu.models.field_report import FieldReport
from ivhuRedu.models.location import Location
from ivhuRedu.models.user import User

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IvhuRedu API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to the IvhuRedu API"}
