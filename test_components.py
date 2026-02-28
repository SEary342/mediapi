"""
Example test script showing how to test components off the Raspberry Pi.

This demonstrates using the modular components without hardware dependencies.
"""

# Example 1: Test Storage (Bookmarks)
from storage import Storage

print("=== Testing Storage ===")
storage = Storage()
bookmarks = storage.load_bookmarks()
print(f"Loaded bookmarks: {bookmarks}")

# Save a new bookmark
bookmarks = storage.save_bookmark(bookmarks, "Song Name", 30000)
print(f"Updated bookmarks: {bookmarks}")


# Example 2: Test Local Library
from local_library import LocalLibrary

print("\n=== Testing Local Library ===")
items = LocalLibrary.get_items(shuffle=False)
print(f"Found {len(items)} local files")
for item in items[:3]:
    print(f"  - {item['name']}")


# Example 3: Test API Clients
from api_clients import JellyfinClient, AudiobookshelfClient

print("\n=== Testing API Clients ===")
try:
    jellyfin_items = JellyfinClient.get_items()
    print(f"Jellyfin: Found {len(jellyfin_items)} items")
except Exception as e:
    print(f"Jellyfin error (expected if not configured): {e}")

try:
    abs_items = AudiobookshelfClient.get_items()
    print(f"Audiobookshelf: Found {len(abs_items)} items")
except Exception as e:
    print(f"Audiobookshelf error (expected if not configured): {e}")


# Example 4: Test Display (without hardware)
from display import Display

print("\n=== Testing Display (Mock) ===")
display = Display(use_hardware=False)
display.clear()
display.draw_text(10, 10, "Hello World", fill="WHITE")
display.draw_rectangle(0, 0, 128, 128, outline="WHITE")
print("Display mock working (no hardware needed)")


# Example 5: Test Input (without hardware)
from input import InputManager

print("\n=== Testing Input (Mock) ===")
input_mgr = InputManager(use_hardware=False)
print(f"UP button pressed: {input_mgr.is_pressed('UP')}")  # Should be False
print("Input mock working (no hardware needed)")


# Example 6: Test Audio (without auto-playing)
from audio import AudioPlayer

print("\n=== Testing Audio ===")
try:
    audio = AudioPlayer()
    print(f"Audio player created, duration: {audio.get_duration()}ms")
    print("Audio player mock working")
except Exception as e:
    print(f"Audio error (expected if VLC not available): {e}")


# Example 7: Test Player in Mock Mode
from player import MP3Player

print("\n=== Testing Player (Mock Mode) ===")
# Initialize with use_hardware=False to avoid GPIO/LCD
# auto_connect_bt=False to skip Bluetooth startup (useful for testing)
player = MP3Player(use_hardware=False, auto_connect_bt=False)
print(f"Player initialized with menu options: {player.menu_options}")
print(f"Current view state: {player.view_state}")
print(f"Scroll index: {player.scroll_index}")

# You can now test various methods without hardware
print("\nPlayer is ready for testing without hardware!")
print("Try things like:")
print("  - player.load_local()")
print("  - player.load_jellyfin()")
print("  - player.render()")
print("  - player.handle_input()")


# Example 8: Test Bluetooth Auto-Connect
print("\n=== Testing Bluetooth Auto-Connect ===")
last_device = storage.load_last_bluetooth_device()
if last_device:
    print(f"Last-used device: {last_device['name']} ({last_device['mac']})")
    print("To test auto-connect on next startup, the device will be auto-connected")
else:
    print("No last-used device found")
    print("After you connect a device, it will be saved for auto-connect")
