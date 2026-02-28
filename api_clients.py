"""API clients for streaming services."""

import requests
import logging
import jellyfin
from jellyfin.api import Version
from jellyfin.generated.api_10_11 import BaseItemKind
from app_config import JELLYFIN, ABS

logger = logging.getLogger(__name__)

# Configurable timeouts (in seconds)
# Increase these if your servers are slow or on unreliable networks
JELLYFIN_TIMEOUT = 15
ABS_TIMEOUT = 15


class JellyfinClient:
    # We initialize these as None and set them up properly
    _api = None
    server_url = JELLYFIN["url"].rstrip("/")
    api_key = JELLYFIN["api"]

    @classmethod
    def get_instance(cls):
        """Lazy loader for the API instance to prevent NoneType errors."""
        if cls._api is None:
            # Note: Ensure Version.V10_11 matches your server version
            cls._api = jellyfin.api(cls.server_url, cls.api_key, Version.V10_11)
        return cls._api

    @classmethod
    def get_items(cls, limit=50):
        """Fetch Audio items from the server."""
        api = cls.get_instance()

        # We use the search abstraction provided by the SDK
        query = api.items.search.add("include_item_types", [BaseItemKind.AUDIO])
        query.recursive = True
        query.limit = limit

        # .all is a property that executes the request
        result = query.all

        return (
            [dict(x) for x in result.data]
            if hasattr(result, "data") and result.data
            else []
        )

    @classmethod
    def get_stream_uri(cls, item_id, container="mp3"):
        """Constructs a direct stream URI for an audio item."""
        # Standard Jellyfin streaming endpoint
        endpoint = f"{cls.server_url}/Audio/{item_id}/stream.{container}"
        return f"{endpoint}?api_key={cls.api_key}"


class AudiobookshelfClient:
    """Audiobookshelf API client."""

    @staticmethod
    def get_items(timeout=None):
        """Fetch items from Audiobookshelf."""
        if timeout is None:
            timeout = ABS_TIMEOUT

        headers = {"Authorization": f"Bearer {ABS['api']}"}
        url = f"{ABS['url']}/api/libraries/{ABS['lib_id']}/items"
        try:
            logger.debug(
                f"Fetching Audiobookshelf items from {ABS['url']} (timeout={timeout}s)"
            )
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
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                logger.error("Audiobookshelf authentication failed - check API key")
                raise Exception(
                    "Audiobookshelf authentication failed - check ABS_API_KEY in .env"
                )
            elif "timeout" in error_msg.lower():
                logger.error(
                    f"Audiobookshelf timeout (network slow or server unresponsive). Try increasing ABS_TIMEOUT in api_clients.py: {e}"
                )
                raise Exception(
                    f"Audiobookshelf timeout - server is slow. Try increasing ABS_TIMEOUT in the code. Error: {e}"
                )
            else:
                logger.error(f"Audiobookshelf API error: {e}")
                raise Exception(f"Audiobookshelf API error: {e}")

    @staticmethod
    def get_stream_uri(item_id):
        """Get stream URI for an Audiobookshelf item."""
        return f"{ABS['url']}/api/items/{item_id}/play?token={ABS['api']}"
