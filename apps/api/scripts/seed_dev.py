#!/usr/bin/env python
# apps/api/scripts/seed_dev.py
"""
One-time ingestion script for development.
Run: python scripts/seed_dev.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_settings
from src.database import SessionLocal
from src.providers import TheOddsApiProvider
from src.services import OddsIngestionService


async def main():
    settings = get_settings()

    if not settings.odds_api_key:
        print("ERROR: ODDS_API_KEY not set in environment")
        print("Set it in .env file or environment variable")
        sys.exit(1)

    print("Starting one-time odds ingestion...")

    db = SessionLocal()
    try:
        provider = TheOddsApiProvider(settings.odds_api_key)
        service = OddsIngestionService(provider, db)
        result = await service.ingest()
        print(f"Success! Ingested {result.games_processed} games with {result.snapshots_created} snapshots")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
