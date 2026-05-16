import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.admin import router as admin_router
from routers.twilio_webhook import router as twilio_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    def _run_migrations():
        from alembic.config import Config
        from alembic import command
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")

    logger.info("Running database migrations...")
    await asyncio.to_thread(_run_migrations)
    logger.info("Migrations complete.")
    yield


app = FastAPI(
    title="AI Infoline API",
    description="AI-based phone infoline SaaS backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(twilio_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
