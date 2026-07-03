"""
================================================================================
Filename: clash_api.py
Description: Client for interacting with the Clash Royale API, including retries, caching, and logging.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-07
Version: 0.4.1
Python Version: 3.12
Dependencies: requests, requests-cache, tenacity
================================================================================

All API requests are available through https://developer.clashroyale.com/#/documentation
"""

from typing import Dict, Any, List
import requests
from requests_cache import CachedSession
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.logger import logger
from app.core.constants import (
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    CACHE_EXPIRATION,
    CACHE_NAME,
    CR_API_BASE_URL,
)


class ClashAPIClient:
    """
    Client for interacting with the Clash Royale API.
    Handles authentication, retries, rate limiting, and caching for API requests.
    """

    def __init__(self) -> None:
        """
        Initialize the ClashAPIClient with API token and base URL.

        Args:
            None (uses settings.CR_API_TOKEN from config).
        """

        self.base_url: str = CR_API_BASE_URL
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {settings.CR_API_TOKEN}",
            "Accept": "application/json",
        }
        # Use CachedSession for caching API responses
        self.session: CachedSession = CachedSession(
            CACHE_NAME,
            backend="sqlite",
            expire_after=CACHE_EXPIRATION,
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def _request(
        self, endpoint: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Clash Royale API with retries and caching.

        Args:
            endpoint: API endpoint (e.g., "/clans/{clan_tag}").
            params: Optional query parameters.

        Returns:
            Dict[str, Any]: JSON response from the API.

        Raises:
            requests.exceptions.RequestException: If the request fails after retries.
        """
        url: str = f"{self.base_url}{endpoint}"
        try:
            logger.info("Fetching endpoint %s", endpoint)
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("API request failed for %s: %s", url, e)
            raise

    def get_clan(self, clan_tag: str) -> Dict[str, Any]:
        """
        Fetch clan data from the Clash Royale API.

        Args:
            clan_tag: The clan tag (e.g., "#ABC123").

        Returns:
            Dict[str, Any]: Clan data, including members, roles, donations, and trophies.
        """
        # Replace '#' with '%23' for URL encoding
        encoded_tag: str = clan_tag.replace("#", "%23")
        return self._request(f"/clans/{encoded_tag}")

    def get_player(self, player_tag: str) -> Dict[str, Any]:
        """
        Fetch player data from the Clash Royale API.

        Args:
            player_tag: The player tag (e.g., "#ABC123").

        Returns:
            Dict[str, Any]: Player data, including trophies, cards, and stats.
        """
        encoded_tag: str = player_tag.replace("#", "%23")
        return self._request(f"/players/{encoded_tag}")

    def get_current_river_race(self, clan_tag: str) -> Dict[str, Any]:
        """
        Fetch the current river race data for a clan.

        Args:
            clan_tag: The clan tag (e.g., "#ABC123").

        Returns:
            Dict[str, Any]: Current river race data, including participants and progress.
        """
        encoded_tag: str = clan_tag.replace("#", "%23")
        return self._request(f"/clans/{encoded_tag}/currentriverrace")

    def get_river_race_log(
        self, clan_tag: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch the river race log for a clan.

        Args:
            clan_tag: The clan tag (e.g., "#ABC123").
            limit: Maximum number of past races to fetch.

        Returns:
            List[Dict[str, Any]]: List of past river race data.
        """
        encoded_tag: str = clan_tag.replace("#", "%23")
        params: Dict[str, Any] = {"limit": limit}
        response: Dict[str, Any] = self._request(
            f"/clans/{encoded_tag}/riverracelog", params
        )
        return response.get("items", [])
