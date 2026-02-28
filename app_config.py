"""Application configuration from environment variables."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Feature toggles
FEATURES = {
    "JELLYFIN": True,
    "ABS": True,
    "LOCAL": True,
    "BT_PAIR": True,
}

# Jellyfin configuration
JELLYFIN = {
    "url": os.getenv("JELLYFIN_URL", "http://YOUR_IP:8096"),
    "api": os.getenv("JELLYFIN_API_KEY", "YOUR_KEY"),
}

# Audiobookshelf configuration
ABS = {
    "url": os.getenv("ABS_URL", "http://YOUR_IP:8000"),
    "api": os.getenv("ABS_API_KEY", "YOUR_KEY"),
    "lib_id": os.getenv("ABS_LIB_ID", "YOUR_LIB_ID"),
}

# Paths
LOCAL_PATH = os.path.expanduser("~/music")
BOOKMARK_FILE = "bookmarks.json"

# Display
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 128
