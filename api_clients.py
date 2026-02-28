"""API clients for streaming services."""

from pathlib import Path

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
    server_url = ABS["url"].rstrip("/")
    api_key = ABS["api"]
    library_id = ABS.get("lib_id")
    # Define local storage path
    DOWNLOAD_DIR = Path.home() / "music" / "abs"

    @classmethod
    def get_items(cls, limit=100):
        """Fetch items and resolve to playable episodes/books."""
        cls.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        headers = {"Authorization": f"Bearer {cls.api_key}"}
        url = f"{cls.server_url}/api/libraries/{cls.library_id}/items"

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            playlist = []
            for item in data.get("results", []):
                if item.get("mediaType") == "podcast":
                    playlist.extend(cls._get_podcast_episodes(item))
                else:
                    # For books, we need the 'ino' (internal node ID) of the audio file
                    # We get this by calling the expanded item API
                    playlist.append(
                        {
                            "name": item.get("media", {})
                            .get("metadata", {})
                            .get("title", "Book"),
                            "id": item["id"],
                            "source": Source.ABS.value,
                            "parent_id": item["id"],
                        }
                    )
            return playlist
        except Exception as e:
            logger.error(f"ABS Library Fetch Error: {e}")
            return []

    @classmethod
    def _get_podcast_episodes(cls, podcast_item):
        """Expand podcast to get episode metadata."""
        headers = {"Authorization": f"Bearer {cls.api_key}"}
        url = f"{cls.server_url}/api/items/{podcast_item['id']}"
        try:
            resp = requests.get(url, headers=headers).json()
            episodes = []
            for ep in resp.get("media", {}).get("episodes", []):
                # We need the 'audioFile' ino to download it
                audio_file = ep.get("audioFile", {})
                episodes.append(
                    {
                        "name": ep.get("title", "Episode"),
                        "id": ep["id"],
                        "ino": audio_file.get("ino"),
                        "parent_id": podcast_item["id"],
                        "source": Source.ABS.value,
                        "ext": audio_file.get("metadata", {}).get("format", "mp3"),
                    }
                )
            return episodes
        except:  # noqa: E722
            return []

    @classmethod
    def get_stream_uri(cls, item):
        """
        Downloads the file if it doesn't exist and returns the local path.
        'item' is the dictionary from the playlist.
        """
        # Create a safe filename
        safe_name = "".join([c if c.isalnum() else "_" for c in item["name"]])
        local_path = cls.DOWNLOAD_DIR / f"{item['id']}_{safe_name}.mp3"

        if local_path.exists():
            logger.info(f"Playing local file: {local_path}")
            return str(local_path)

        # If not local, download it
        logger.info(f"Downloading {item['name']} from ABS...")

        # Determine the download URL
        # For episodes/files, ABS uses: /api/items/{libraryItemId}/file/{ino}/download
        # To simplify, we can use the library item's download endpoint
        download_url = f"{cls.server_url}/api/items/{item['parent_id']}/download?token={cls.api_key}"

        # Note: For specific episodes, you might need the ino-based URL:
        if item.get("ino"):
            download_url = f"{cls.server_url}/api/items/{item['parent_id']}/file/{item['ino']}/download?token={cls.api_key}"

        try:
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return str(local_path)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            # Fallback to the obtuse stream URL if download fails
            return f"{cls.server_url}/api/items/{item['id']}/play?token={cls.api_key}"
