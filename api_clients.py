"""API clients for streaming services."""
import requests
import logging
from app_config import JELLYFIN, ABS

logger = logging.getLogger(__name__)

# Configurable timeouts (in seconds)
# Increase these if your servers are slow or on unreliable networks
JELLYFIN_TIMEOUT = 15
ABS_TIMEOUT = 15


class JellyfinClient:
    """Jellyfin API client."""

    _user_id_cache = None

    @staticmethod
    def _resolve_user_id(timeout=None):
        """Resolve username to user ID if needed."""
        if timeout is None:
            timeout = JELLYFIN_TIMEOUT

        if JellyfinClient._user_id_cache:
            return JellyfinClient._user_id_cache

        user_id = JELLYFIN['user']

        # If it looks like a UUID (contains hyphens), assume it's already correct
        if '-' in user_id:
            JellyfinClient._user_id_cache = user_id
            return user_id

        # Otherwise, try to resolve the username to a user ID
        logger.debug(f"Resolving Jellyfin username '{user_id}' to user ID...")
        try:
            url = f"{JELLYFIN['url']}/Users?api_key={JELLYFIN['api']}"
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            users = response.json()

            # Find user by name (case-insensitive)
            for user in users:
                if user.get('Name', '').lower() == user_id.lower():
                    resolved_id = user['Id']
                    logger.info(f"Resolved username '{user_id}' to ID '{resolved_id}'")
                    JellyfinClient._user_id_cache = resolved_id
                    return resolved_id

            # User not found
            available_users = [u.get('Name', 'Unknown') for u in users]
            logger.error(f"Jellyfin user '{user_id}' not found. Available users: {available_users}")
            raise Exception(
                f"Jellyfin user '{user_id}' not found. Available users: {available_users}. "
                f"Set JELLYFIN_USER_ID in .env to one of these names or their UUID."
            )

        except requests.RequestException as e:
            logger.error(f"Failed to resolve Jellyfin user: {e}")
            raise Exception(f"Failed to resolve Jellyfin user: {e}")

    @staticmethod
    def get_items(timeout=None):
        """Fetch audio items from Jellyfin."""
        if timeout is None:
            timeout = JELLYFIN_TIMEOUT

        try:
            # Resolve user ID
            user_id = JellyfinClient._resolve_user_id(timeout=timeout)

            url = f"{JELLYFIN['url']}/Users/{user_id}/Items?IncludeItemTypes=Audio&Recursive=True&SortBy=SortName&api_key={JELLYFIN['api']}"
            logger.debug(f"Fetching Jellyfin items from {JELLYFIN['url']} (timeout={timeout}s)")
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
            error_msg = str(e)
            if '400' in error_msg or 'Bad Request' in error_msg:
                logger.error(f"Jellyfin 400 error - check JELLYFIN_USER_ID in .env (should be UUID or valid username): {e}")
                raise Exception(
                    f"Jellyfin Bad Request (400) - Verify JELLYFIN_USER_ID is correct. "
                    f"Should be either the username or a UUID (with hyphens). Error: {e}"
                )
            elif '401' in error_msg or 'Unauthorized' in error_msg:
                logger.error("Jellyfin authentication failed - check API key")
                raise Exception("Jellyfin authentication failed - check JELLYFIN_API_KEY in .env")
            elif 'timeout' in error_msg.lower():
                logger.error(f"Jellyfin timeout (network slow or server unresponsive). Try increasing JELLYFIN_TIMEOUT in api_clients.py: {e}")
                raise Exception(f"Jellyfin timeout - server is slow. Try increasing JELLYFIN_TIMEOUT in the code. Error: {e}")
            else:
                logger.error(f"Jellyfin API error: {e}")
                raise Exception(f"Jellyfin API error: {e}")

    @staticmethod
    def get_stream_uri(item_id):
        """Get stream URI for a Jellyfin audio item."""
        return f"{JELLYFIN['url']}/Audio/{item_id}/stream?static=true&api_key={JELLYFIN['api']}"


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
            logger.debug(f"Fetching Audiobookshelf items from {ABS['url']} (timeout={timeout}s)")
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
            if '401' in error_msg or 'Unauthorized' in error_msg:
                logger.error("Audiobookshelf authentication failed - check API key")
                raise Exception("Audiobookshelf authentication failed - check ABS_API_KEY in .env")
            elif 'timeout' in error_msg.lower():
                logger.error(f"Audiobookshelf timeout (network slow or server unresponsive). Try increasing ABS_TIMEOUT in api_clients.py: {e}")
                raise Exception(f"Audiobookshelf timeout - server is slow. Try increasing ABS_TIMEOUT in the code. Error: {e}")
            else:
                logger.error(f"Audiobookshelf API error: {e}")
                raise Exception(f"Audiobookshelf API error: {e}")

    @staticmethod
    def get_stream_uri(item_id):
        """Get stream URI for an Audiobookshelf item."""
        return f"{ABS['url']}/api/items/{item_id}/play?token={ABS['api']}"
