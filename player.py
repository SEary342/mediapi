"""Main MP3 player application."""

from utils import Source

import logging
import threading
import time
import random

from app_config import FEATURES
from api_clients import JellyfinClient, AudiobookshelfClient
from local_library import LocalLibrary
from audio import AudioPlayer
from bluetooth import BluetoothManager
from display import Display
from input import InputManager
from server import run_server
from storage import Storage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mediapi.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class MP3Player:
    """Main music player application."""

    def __init__(self, use_hardware=True, auto_connect_bt=True):
        """Initialize the MP3 player."""
        logger.info("Initializing MP3 Player...")

        # Initialize components
        self.display = Display(use_hardware=use_hardware)
        self.input = InputManager(use_hardware=use_hardware)
        self.audio = AudioPlayer()
        self.storage = Storage()

        # Start the web server in a background thread
        server_thread = threading.Thread(target=run_server, args=(self,), daemon=True)
        server_thread.start()

        # App state
        self.playlist = []
        self.bt_devices = []
        self.current_index = 0
        self.scroll_index = 0
        self.view_state = "MENU"
        self.menu_options = []

        # Build menu based on features
        if FEATURES["JELLYFIN"]:
            self.menu_options.extend(["Jellyfin", "Jellyfin Shuffle"])
        if FEATURES["ABS"]:
            self.menu_options.append("Audiobookshelf")
        if FEATURES["LOCAL"]:
            self.menu_options.extend(["Local Files", "Local Shuffle"])
        if FEATURES["BT_PAIR"]:
            self.menu_options.append("Bluetooth Pair")

        # Load bookmarks
        self.bookmarks = self.storage.load_bookmarks()
        self.last_save_time = time.time()

        # Auto-connect to last Bluetooth device
        if auto_connect_bt:
            logger.info("Attempting auto-connect to last Bluetooth device...")
            if BluetoothManager.auto_connect_last_device():
                self.draw_message("BLUETOOTH", "Connected!", color="GREEN")
                time.sleep(1)
            else:
                logger.debug("Auto-connect skipped or failed")

        logger.info("MP3 Player initialized successfully")

    def play(self):
        """Play the current track."""
        if self.view_state == "PLAYING":
            self.audio.play()

    def pause(self):
        """Pause the current track."""
        if self.view_state == "PLAYING":
            self.audio.pause()

    def next(self):
        """Go to the next track."""
        if self.view_state == "PLAYING":
            self.play_selection((self.current_index + 1) % len(self.playlist))

    def previous(self):
        """Go to the previous track."""
        if self.view_state == "PLAYING":
            self.play_selection((self.current_index - 1) % len(self.playlist))

    # --- Content Loading ---
    def load_jellyfin(self, shuffle=False):
        """Load playlist from Jellyfin."""
        try:
            self.playlist = JellyfinClient.get_items()
            if shuffle:
                random.shuffle(self.playlist)
                self.play_selection(0)
            else:
                self.view_state, self.scroll_index = "BROWSER", 0
        except Exception as e:
            self.draw_error(f"Jellyfin Fail: {str(e)[:15]}")

    def load_abs(self):
        """Load playlist from Audiobookshelf."""
        try:
            self.playlist = AudiobookshelfClient.get_items()
            self.view_state, self.scroll_index = "BROWSER", 0
        except Exception as e:
            self.draw_error(f"ABS Fail: {str(e)[:15]}")

    def load_local(self, shuffle=False):
        """Load local files."""
        items = LocalLibrary.get_items(shuffle=shuffle)
        if not items:
            self.draw_error("No Local Files")
            return

        self.playlist = items

        if shuffle:
            self.play_selection(0)
        else:
            self.view_state, self.scroll_index = "BROWSER", 0

    # --- Playback Control ---
    def play_selection(self, index):
        """Play a selected item."""
        self.save_bookmark()
        self.current_index = index
        item = self.playlist[index]

        # Get stream URI
        if item["source"] == Source.LOCAL.value:
            uri = LocalLibrary.get_stream_uri(item)
        elif item["source"] == Source.JELLYFIN.value:
            uri = JellyfinClient.get_stream_uri(item["id"])
        elif item["source"] == Source.ABS.value:
            uri = AudiobookshelfClient.get_stream_uri(item["id"])
        else:
            return

        # Load and play
        self.audio.load_uri(uri)

        # Restore bookmark if exists
        bookmark = self.storage.get_bookmark(self.bookmarks, item["name"])
        if bookmark is not None:
            self.audio.set_time(bookmark)

        self.view_state = "PLAYING"

    def save_bookmark(self):
        """Save current playback position."""
        if self.playlist and self.view_state == "PLAYING":
            item = self.playlist[self.current_index]
            pos = self.audio.get_time()
            self.bookmarks = self.storage.save_bookmark(
                self.bookmarks, item["name"], pos
            )

    def jump_to_letter(self, direction):
        """Jump to next/previous letter in playlist."""
        if not self.playlist or self.view_state != "BROWSER":
            return

        curr = self.playlist[self.scroll_index]["name"][0].upper()

        if direction == 1:
            # Jump forward
            for i in range(self.scroll_index + 1, len(self.playlist)):
                if self.playlist[i]["name"][0].upper() > curr:
                    self.scroll_index = i
                    return
        else:
            # Jump backward
            for i in range(self.scroll_index - 1, -1, -1):
                if self.playlist[i]["name"][0].upper() < curr:
                    t = self.playlist[i]["name"][0].upper()
                    while i > 0 and self.playlist[i - 1]["name"][0].upper() == t:
                        i -= 1
                    self.scroll_index = i
                    return

    # --- Bluetooth ---
    def scan_bluetooth(self):
        """Scan for Bluetooth devices."""
        self.draw_message("BLUETOOTH", "Scanning (5s)...")
        try:
            self.bt_devices = BluetoothManager.scan_devices()
            if not self.bt_devices:
                self.draw_error("No BT Devices")
                self.view_state = "MENU"
            else:
                self.view_state, self.scroll_index = "BT_SCAN", 0
        except Exception as e:
            self.draw_error(f"BT Fail: {str(e)[:15]}")

    def connect_bluetooth(self, index):
        """Connect to a Bluetooth device."""
        if index >= len(self.bt_devices):
            return

        device = self.bt_devices[index]
        self.draw_message("CONNECTING", device["name"][:15])

        try:
            BluetoothManager.connect(device["mac"], device["name"])
            self.draw_message("SUCCESS", "Audio Routed!", color="GREEN")
            time.sleep(2)
        except Exception as e:
            self.draw_error(f"BT Error: {str(e)[:15]}")

        self.view_state, self.scroll_index = "MENU", 0

    # --- UI Rendering ---
    def draw_message(self, title, msg, color="BLUE"):
        """Draw a message on the display."""
        self.display.clear()
        self.display.draw_rectangle(0, 0, 128, 128, fill=color)
        self.display.draw_text(10, 45, title, fill="WHITE")
        self.display.draw_text(10, 65, msg[:18], fill="WHITE")
        self.display.show_image()

    def draw_error(self, msg):
        """Draw an error message."""
        self.display.clear()
        self.display.draw_rectangle(0, 0, 128, 128, fill="RED")
        self.display.draw_text(10, 50, "ERROR:", fill="WHITE")
        self.display.draw_text(10, 70, msg, fill="WHITE")
        self.display.show_image()
        time.sleep(2)

    def render(self):
        """Render the current view."""
        self.display.clear()

        if self.view_state == "MENU":
            self.display.draw_text(5, 5, "-- SOURCES --", fill="YELLOW")
            for i, opt in enumerate(self.menu_options):
                color = "WHITE" if self.scroll_index == i else "GRAY"
                self.display.draw_text(10, 25 + (i * 18), opt, fill=color)

        elif self.view_state == "BROWSER":
            src = self.playlist[0]["source"] if self.playlist else ""
            self.display.draw_text(5, 5, f"-- {src} --", fill="CYAN")
            start = max(0, self.scroll_index - 2)
            for i in range(5):
                idx = start + i
                if idx < len(self.playlist):
                    is_bk = "*" if self.playlist[idx]["name"] in self.bookmarks else ""
                    color = "WHITE" if idx == self.scroll_index else "GRAY"
                    self.display.draw_text(
                        10,
                        25 + (i * 18),
                        f"{is_bk}{self.playlist[idx]['name'][:14]}",
                        fill=color,
                    )

        elif self.view_state == "BT_SCAN":
            self.display.draw_text(5, 5, "-- DEVICES --", fill="MAGENTA")
            start = max(0, self.scroll_index - 2)
            for i in range(5):
                idx = start + i
                if idx < len(self.bt_devices):
                    color = "WHITE" if idx == self.scroll_index else "GRAY"
                    self.display.draw_text(
                        10,
                        25 + (i * 18),
                        self.bt_devices[idx]["name"][:14],
                        fill=color,
                    )

        elif self.view_state == "PLAYING":
            song = self.playlist[self.current_index]
            self.display.draw_text(5, 10, "NOW PLAYING", fill="GREEN")
            self.display.draw_text(5, 40, song["name"][:18], fill="WHITE")
            # Use duration from item metadata if available, otherwise use audio player duration
            length = song.get("duration") or self.audio.get_duration()
            cur = self.audio.get_time()
            if length > 0 and cur >= 0:
                bar = int((cur / length) * 110)
                self.display.draw_rectangle(10, 75, 120, 80, outline="WHITE")
                self.display.draw_rectangle(10, 75, 10 + bar, 80, fill="BLUE")

        self.display.show_image()

    # --- Input Handling ---
    def handle_input(self):
        """Handle button inputs."""
        # UP/DOWN Navigation
        if self.input.is_pressed("UP"):
            self.scroll_index = max(0, self.scroll_index - 1)
            time.sleep(0.15)

        if self.input.is_pressed("DOWN"):
            limit = (
                len(self.menu_options)
                if self.view_state == "MENU"
                else (
                    len(self.playlist)
                    if self.view_state == "BROWSER"
                    else len(self.bt_devices)
                )
            )
            if limit > 0:
                self.scroll_index = min(limit - 1, self.scroll_index + 1)
            time.sleep(0.15)

        # SELECTION (PRESS or KEY2)
        if self.input.is_pressed("PRESS") or self.input.is_pressed("KEY2"):
            if self.view_state == "MENU":
                choice = self.menu_options[self.scroll_index]
                if choice == "Jellyfin":
                    self.load_jellyfin(shuffle=False)
                elif choice == "Jellyfin Shuffle":
                    self.load_jellyfin(shuffle=True)
                elif "Audiobook" in choice:
                    self.load_abs()
                elif "Local Files" in choice:
                    self.load_local(shuffle=False)
                elif "Shuffle" in choice:
                    self.load_local(shuffle=True)
                elif "Bluetooth" in choice:
                    self.scan_bluetooth()
            elif self.view_state == "BROWSER":
                self.play_selection(self.scroll_index)
            elif self.view_state == "BT_SCAN":
                self.connect_bluetooth(self.scroll_index)
            elif self.view_state == "PLAYING":
                self.audio.pause()
                self.save_bookmark()
            time.sleep(0.3)

        # BACK (KEY1)
        if self.input.is_pressed("KEY1"):
            self.save_bookmark()
            self.view_state, self.scroll_index = "MENU", 0
            time.sleep(0.3)

        # LEFT/RIGHT (Skip/Letter Jump)
        if self.input.is_pressed("LEFT"):
            if self.view_state == "BROWSER":
                self.jump_to_letter(-1)
            elif self.view_state == "PLAYING":
                pos = self.audio.get_time()
                self.audio.set_time(max(0, pos - 15000))
            time.sleep(0.2)

        if self.input.is_pressed("RIGHT"):
            if self.view_state == "BROWSER":
                self.jump_to_letter(1)
            elif self.view_state == "PLAYING":
                pos = self.audio.get_time()
                duration = self.audio.get_duration()
                self.audio.set_time(min(duration - 100, pos + 30000))
            time.sleep(0.2)

    def run(self):
        """Main application loop."""
        try:
            while True:
                self.handle_input()
                if (
                    self.view_state == "PLAYING"
                    and time.time() - self.last_save_time > 15
                ):
                    self.save_bookmark()
                    self.last_save_time = time.time()
                # Auto-play next track when current finishes
                if self.view_state == "PLAYING" and not self.audio.is_playing():
                    if self.current_index < len(self.playlist) - 1:
                        self.next()
                    else:
                        # Loop back to start of playlist
                        self.play_selection(0)
                self.render()
                time.sleep(0.05)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """Clean up resources."""
        self.save_bookmark()
        self.input.cleanup()
        self.display.cleanup()


if __name__ == "__main__":
    # For testing off the Pi, use use_hardware=False
    app = MP3Player(use_hardware=True)
    app.run()
