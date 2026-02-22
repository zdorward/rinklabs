# apps/api/src/routers/users.py
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User
from src.auth import get_current_user, require_user, require_pro

router = APIRouter()


class UserResponse(BaseModel):
    id: UUID
    email: str | None
    subscription_status: str
    current_period_end: datetime | None


class ProMarketsResponse(BaseModel):
    message: str


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_user)):
    """Get current user info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        subscription_status=user.subscription_status,
        current_period_end=user.current_period_end,
    )


@router.get("/pro/markets/today")
async def get_pro_markets(
    user: User = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Get full market board for pro users."""
    return {"access": "pro", "user_id": str(user.id)}
