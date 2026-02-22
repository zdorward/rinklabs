# apps/api/src/providers/the_odds_api.py
import httpx
from datetime import datetime, timezone
import logging

from src.providers.base import OddsProvider, GameOdds, BookmakerOdds

logger = logging.getLogger(__name__)


class TheOddsApiProvider(OddsProvider):
    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_nhl_odds(self) -> list[GameOdds]:
        """Fetch NHL moneyline odds for upcoming games."""
        url = f"{self.BASE_URL}/sports/icehockey_nhl/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        games = []
        for game_data in data:
            bookmakers = []
            for book in game_data.get("bookmakers", []):
                outcomes = {
                    o["name"]: o["price"]
                    for o in book.get("markets", [{}])[0].get("outcomes", [])
                }
                home_team = game_data["home_team"]
                away_team = game_data["away_team"]

                if home_team in outcomes and away_team in outcomes:
                    bookmakers.append(
                        BookmakerOdds(
                            key=book["key"],
                            title=book["title"],
                            home_price=outcomes[home_team],
                            away_price=outcomes[away_team],
                        )
                    )

            if bookmakers:
                games.append(
                    GameOdds(
                        external_id=game_data["id"],
                        home_team=game_data["home_team"],
                        away_team=game_data["away_team"],
                        commence_time=datetime.fromisoformat(
                            game_data["commence_time"].replace("Z", "+00:00")
                        ),
                        bookmakers=bookmakers,
                    )
                )

        logger.info(f"Fetched {len(games)} NHL games with odds")
        return games
