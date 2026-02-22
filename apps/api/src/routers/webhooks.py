# apps/api/src/routers/webhooks.py
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db
from src.models import User

router = APIRouter()
settings = get_settings()
stripe.api_key = settings.stripe_secret_key


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        clerk_user_id = session.get("metadata", {}).get("clerk_user_id")

        if clerk_user_id:
            user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
            if user:
                user.stripe_customer_id = session.get("customer")
                user.subscription_id = session.get("subscription")
                user.subscription_status = "active"
                user.updated_at = datetime.now(timezone.utc)
                db.commit()

    elif event["type"] == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")

        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = sub.get("status", "active")
            if sub.get("current_period_end"):
                user.current_period_end = datetime.fromtimestamp(
                    sub["current_period_end"], tz=timezone.utc
                )
            user.updated_at = datetime.now(timezone.utc)
            db.commit()

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")

        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = "canceled"
            user.updated_at = datetime.now(timezone.utc)
            db.commit()

    return {"received": True}
