# apps/api/src/routers/__init__.py
from src.routers.health import router as health_router
from src.routers.games import router as games_router
from src.routers.markets import router as markets_router
from src.routers.users import router as users_router
from src.routers.webhooks import router as webhooks_router

__all__ = [
    "health_router",
    "games_router",
    "markets_router",
    "users_router",
    "webhooks_router",
]
