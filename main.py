from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ivhuRedu.routers.location import router as location_router
from ivhuRedu.routers import broadcasts

app = FastAPI(title="IvhuRedu Agricultural Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(broadcasts.router)
app.include_router(location_router)

@app.get("/")
async def root():
    return {"status": "ok"}
