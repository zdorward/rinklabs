# apps/api/src/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.scheduler import setup_scheduler, shutdown_scheduler
from src.routers import (
    health_router,
    games_router,
    markets_router,
    users_router,
    webhooks_router,
)

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - start/stop scheduler."""
    logger.info("Starting application")
    setup_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Application stopped")


app = FastAPI(
    title="Rinklabs API",
    description="Hockey market intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://rinklabs.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(games_router)
app.include_router(markets_router)
app.include_router(users_router)
app.include_router(webhooks_router)
