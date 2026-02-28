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
    """Audiobookshelf API client using standard requests."""

    server_url = ABS["url"].rstrip("/")
    api_key = ABS["api"]
    library_id = ABS.get("lib_id")  # Ensure this is in your app_config

    @classmethod
    def get_items(cls, limit=50):
        """
        Fetch items from Audiobookshelf.
        Note: ABS returns Books/Podcasts. We flatten them into 'Tracks'.
        """
        headers = {"Authorization": f"Bearer {cls.api_key}"}
        # Get all items in the specified library
        url = f"{cls.server_url}/api/libraries/{cls.library_id}/items"

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()  # This returns a dict with a "results" list

            playlist = []
            # ABS items are containers (Books). We need to get the audio files inside.
            for book in data.get("results", []):
                # We need to fetch the 'expanded' item to see the tracks
                # For a simple MP3 player, we'll treat the Book Title as the track name
                # and use the first audio file found.

                item_name = (
                    book.get("media", {})
                    .get("metadata", {})
                    .get("title", "Unknown Book")
                )
                item_id = book.get("id")

                # We store the item_id. In get_stream_uri, we use the 'play' endpoint
                # which ABS handles by streaming the combined book or the first file.
                playlist.append(
                    {
                        "name": item_name,
                        "id": item_id,
                        "source": Source.ABS.value,
                        "author": book.get("media", {})
                        .get("metadata", {})
                        .get("authorName", "Unknown"),
                    }
                )

                if len(playlist) >= limit:
                    break

            logger.info(f"ABS: Loaded {len(playlist)} items")
            return playlist

        except Exception as e:
            logger.error(f"Audiobookshelf Error: {e}")
            return []

    @classmethod
    def get_stream_uri(cls, item_id):
        """
        Constructs a stream URI for an ABS item.
        The /api/items/{id}/play endpoint is the most compatible with VLC.
        """
        # We append the token as a query param so VLC can authenticate the stream
        return f"{cls.server_url}/api/items/{item_id}/play?token={cls.api_key}"
