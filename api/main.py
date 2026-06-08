import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.admin import router as admin_router
from routers.portal import router as portal_router
from routers.telnyx_webhook import router as telnyx_router

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-8s %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "services": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "routers": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "__main__": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import subprocess
    logger.info("Running database migrations...")
    await asyncio.to_thread(
        lambda: subprocess.run(["alembic", "upgrade", "head"], check=True)
    )
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
app.include_router(portal_router)
app.include_router(telnyx_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
