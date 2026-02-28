"""API clients for streaming services."""
import requests
import logging
from app_config import JELLYFIN, ABS

logger = logging.getLogger(__name__)


class JellyfinClient:
    """Jellyfin API client."""

    @staticmethod
    def get_items(timeout=4):
        """Fetch audio items from Jellyfin."""
        url = f"{JELLYFIN['url']}/Users/{JELLYFIN['user']}/Items?IncludeItemTypes=Audio&Recursive=True&SortBy=SortName&api_key={JELLYFIN['api']}"
        try:
            logger.debug(f"Fetching Jellyfin items from {JELLYFIN['url']}")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            items = [
                {"name": i["Name"], "id": i["Id"], "source": "JELLY"}
                for i in data.get("Items", [])
            ]
            logger.info(f"Loaded {len(items)} items from Jellyfin")
            return items
        except requests.RequestException as e:
            logger.error(f"Jellyfin API error: {e}")
            raise Exception(f"Jellyfin API error: {e}")

    @staticmethod
    def get_stream_uri(item_id):
        """Get stream URI for a Jellyfin audio item."""
        return f"{JELLYFIN['url']}/Audio/{item_id}/stream?static=true&api_key={JELLYFIN['api']}"


class AudiobookshelfClient:
    """Audiobookshelf API client."""

    @staticmethod
    def get_items(timeout=4):
        """Fetch items from Audiobookshelf."""
        headers = {"Authorization": f"Bearer {ABS['api']}"}
        url = f"{ABS['url']}/api/libraries/{ABS['lib_id']}/items"
        try:
            logger.debug(f"Fetching Audiobookshelf items from {ABS['url']}")
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            items = [
                {
                    "name": i["media"]["metadata"]["title"],
                    "id": i["id"],
                    "source": "ABS",
                }
                for i in data.get("results", [])
            ]
            logger.info(f"Loaded {len(items)} items from Audiobookshelf")
            return items
        except requests.RequestException as e:
            logger.error(f"Audiobookshelf API error: {e}")
            raise Exception(f"Audiobookshelf API error: {e}")

    @staticmethod
    def get_stream_uri(item_id):
        """Get stream URI for an Audiobookshelf item."""
        return f"{ABS['url']}/api/items/{item_id}/play?token={ABS['api']}"
