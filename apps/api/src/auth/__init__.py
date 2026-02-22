# apps/api/src/auth/__init__.py
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import jwt
import httpx

from src.config import get_settings
from src.database import get_db
from src.models import User

settings = get_settings()

# Cache for JWKS
_jwks_cache: dict = {}


async def get_clerk_jwks(issuer: str) -> dict:
    """Fetch Clerk's JWKS for token verification."""
    if issuer in _jwks_cache:
        return _jwks_cache[issuer]

    jwks_url = f"{issuer}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        if response.status_code == 200:
            _jwks_cache[issuer] = response.json()
            return _jwks_cache[issuer]
    return {}


async def verify_clerk_token(token: str) -> dict | None:
    """Verify Clerk JWT and return claims."""
    try:
        # Decode header to get key ID and issuer
        unverified = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified.get("iss")

        if not issuer:
            return None

        # Get JWKS from Clerk
        jwks = await get_clerk_jwks(issuer)
        if not jwks:
            return None

        # Get the signing key
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                break

        if not key:
            return None

        # Verify and decode the token
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False}  # Clerk doesn't always set audience
        )
        return claims
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
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
