"""API clients for streaming services."""

from utils import Source

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

        items = []
        if hasattr(result, "data") and result.data:
            for x in result.data:
                item_dict = {**dict(x), "source": Source.JELLYFIN.value}
                # Convert RunTimeTicks (100-nanosecond intervals) to milliseconds
                if hasattr(x, "run_time_ticks") and x.run_time_ticks:
                    item_dict["duration"] = x.run_time_ticks // 10000
                items.append(item_dict)
        return items

    @classmethod
    def get_stream_uri(cls, item_id, container="mp3"):
        """Constructs a direct stream URI for an audio item."""
        # Standard Jellyfin streaming endpoint
        endpoint = f"{cls.server_url}/Audio/{item_id}/stream.{container}"
        return f"{endpoint}?api_key={cls.api_key}"


class AudiobookshelfClient:
    """Audiobookshelf API client for Podcasts and Books."""

    server_url = ABS["url"].rstrip("/")
    api_key = ABS["api"]
    library_id = ABS.get("lib_id")

    @classmethod
    def get_items(cls, limit=100):
        """
        Fetch items and drill down into Podcasts to get Episodes.
        """
        headers = {"Authorization": f"Bearer {cls.api_key}"}
        # Get all items in the library
        url = f"{cls.server_url}/api/libraries/{cls.library_id}/items"

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            playlist = []
            for item in data.get("results", []):
                # Check if this is a Podcast
                if item.get("mediaType") == "podcast":
                    # We must "drill down" to get episodes for this podcast
                    episodes = cls._get_podcast_episodes(item["id"])
                    playlist.extend(episodes)
                else:
                    # It's a Book - use the standard container
                    playlist.append(
                        {
                            "name": item.get("media", {})
                            .get("metadata", {})
                            .get("title", "Unknown Book"),
                            "id": item["id"],
                            "source": Source.ABS.value,
                            "type": "book",
                        }
                    )

                if len(playlist) >= limit:
                    break

            logger.info(f"ABS: Flattened into {len(playlist)} playable tracks")
            return playlist

        except Exception as e:
            logger.error(f"Audiobookshelf Error fetching library: {e}")
            return []

    @classmethod
    def _get_podcast_episodes(cls, podcast_id):
        """Fetch individual episodes for a podcast ID."""
        headers = {"Authorization": f"Bearer {cls.api_key}"}
        # We need the expanded podcast object to see episodes
        url = f"{cls.server_url}/api/items/{podcast_id}"

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            episodes_data = data.get("media", {}).get("episodes", [])

            episodes = []
            for ep in episodes_data:
                episodes.append(
                    {
                        # Name shown in browser: "Podcast Title - Episode Title"
                        "name": f"{ep.get('title', 'Unknown Episode')}",
                        "id": ep["id"],  # This is the Episode ID
                        "source": Source.ABS.value,
                        "type": "episode",
                    }
                )
            return episodes
        except Exception as e:
            logger.error(f"Error drilling into podcast {podcast_id}: {e}")
            return []

    @classmethod
    def get_stream_uri(cls, item_id):
        """
        Get stream URI.
        Note: For episodes, the endpoint is /api/items/{podcast_id}/play/{episode_id}
        But ABS allows /api/items/{episode_id}/play as well if it's a valid ID.
        """
        # VLC needs the token in the URL for authentication
        return f"{cls.server_url}/api/items/{item_id}/play?token={cls.api_key}"
