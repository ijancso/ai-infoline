from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.twilio_webhook import router as twilio_router

app = FastAPI(
    title="AI Infoline API",
    description="AI-based phone infoline SaaS backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(twilio_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
