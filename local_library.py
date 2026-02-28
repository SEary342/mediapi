"""Local file library management."""
from utils import Source
import os
import random
from app_config import LOCAL_PATH


class LocalLibrary:
    """Manages local music files."""

    SUPPORTED_FORMATS = (".mp3", ".m4a", ".wav")

    @staticmethod
    def get_items(shuffle=False):
        """Get list of local music files."""
        if not os.path.exists(LOCAL_PATH):
            os.makedirs(LOCAL_PATH)

        files = [
            f
            for f in os.listdir(LOCAL_PATH)
            if f.lower().endswith(LocalLibrary.SUPPORTED_FORMATS)
        ]

        if not files:
            return []

        items = [
            {"name": f, "path": os.path.join(LOCAL_PATH, f), "source": Source.LOCAL.value}
            for f in sorted(files)
        ]

        if shuffle:
            random.shuffle(items)

        return items

    @staticmethod
    def get_stream_uri(item):
        """Get stream URI for a local file."""
        return item.get("path", "")
