"""Bookmark and persistence management."""
import json
import os
from app_config import BOOKMARK_FILE

BLUETOOTH_DEVICE_FILE = "bt_device.json"


class Storage:
    """Handles bookmark persistence."""

    @staticmethod
    def load_bookmarks():
        """Load bookmarks from file."""
        if os.path.exists(BOOKMARK_FILE):
            try:
                with open(BOOKMARK_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @staticmethod
    def save_bookmark(bookmarks, item_name, position):
        """Save a bookmark for an item."""
        if position > 0:
            bookmarks[item_name] = position
            with open(BOOKMARK_FILE, "w") as f:
                json.dump(bookmarks, f)
        return bookmarks

    @staticmethod
    def get_bookmark(bookmarks, item_name):
        """Get bookmark position for an item."""
        return bookmarks.get(item_name, None)

    @staticmethod
    def save_last_bluetooth_device(mac_address, device_name):
        """Save the last-used Bluetooth device."""
        data = {"mac": mac_address, "name": device_name}
        try:
            with open(BLUETOOTH_DEVICE_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    @staticmethod
    def load_last_bluetooth_device():
        """Load the last-used Bluetooth device."""
        if os.path.exists(BLUETOOTH_DEVICE_FILE):
            try:
                with open(BLUETOOTH_DEVICE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

