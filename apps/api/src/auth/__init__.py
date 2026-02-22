# apps/api/src/auth/__init__.py
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import httpx

from src.config import get_settings
from src.database import get_db
from src.models import User

settings = get_settings()


async def verify_clerk_token(token: str) -> dict | None:
    """Verify Clerk JWT and return session claims."""
    if not settings.clerk_secret_key:
        return None

    # For production, use Clerk's official SDK
    # This is a simplified version for MVP
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.clerk.com/v1/sessions/verify",
                headers={
                    "Authorization": f"Bearer {settings.clerk_secret_key}",
                },
                params={"token": token},
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


def get_or_create_user(db: Session, clerk_id: str, email: str | None = None) -> User:
    """Get existing user or create new one."""
    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        user = User(clerk_id=clerk_id, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif email and user.email != email:
        user.email = email
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
    return user


async def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Get current user from Clerk JWT.
    Returns None if no auth header (for optional auth routes).
    """
    if not authorization:
        return None

    token = authorization.replace("Bearer ", "")
    claims = await verify_clerk_token(token)

    if not claims:
        return None

    user_id = claims.get("user_id") or claims.get("sub")
    email = claims.get("email")

    if not user_id:
        return None

    return get_or_create_user(db, clerk_id=user_id, email=email)


async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """Dependency that requires authenticated user."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_pro(
    user: User = Depends(require_user),
) -> User:
    """Dependency that requires active subscription."""
    if user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Pro subscription required")
    return user
