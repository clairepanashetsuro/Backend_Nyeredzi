from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ivhuRedu.routers.sms import router as sms_router
from dotenv import load_dotenv
import os

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ivhuRedu.routers.sms import router as sms_router

app = FastAPI(
    title="Ivhuredu SMS Gateway Component Gateway Service Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sms_router)