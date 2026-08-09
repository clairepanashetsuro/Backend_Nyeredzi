from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from ivhuRedu.routers.broadcasts import router as broadcasts_router

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="IvhuRedu Agricultural Platform API", version="1.0.0")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(broadcasts_router)

@app.get("/")
async def root():
    return {"status": "ok"}
