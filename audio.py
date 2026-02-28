"""Audio playback management."""
import time
import vlc


class AudioPlayer:
    """Manages VLC audio playback."""

    def __init__(self):
        """Initialize VLC instance."""
        instance = vlc.Instance(
            "--no-video", "--network-caching=3000", "--aout=pulse"
        )
        self.player = instance.media_player_new()
        self.instance = instance

    def load_uri(self, uri):
        """Load and play a URI."""
        media = self.instance.media_new(uri)
        self.player.set_media(media)
        self.player.play()
        time.sleep(0.6)

    def play(self):
        """Resume playback."""
        self.player.play()

    def pause(self):
        """Pause playback."""
        self.player.pause()

    def get_time(self):
        """Get current playback position in milliseconds."""
        return self.player.get_time()

    def set_time(self, position):
        """Set playback position in milliseconds."""
        self.player.set_time(position)

    def get_duration(self):
        """Get total duration in milliseconds."""
        return self.player.get_length()

    def is_playing(self):
        """Check if currently playing."""
        return self.player.is_playing()
