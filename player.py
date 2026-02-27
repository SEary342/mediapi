import LCD_1in44
import time
import vlc
import requests
import os
import json
from PIL import Image, ImageDraw, ImageFont

# --- FEATURE TOGGLES ---
# Set to False to hide/disable specific sources
FEATURES = {"JELLYFIN": False, "ABS": False, "LOCAL": True, "BT_PAIR": True}

# --- Configuration ---
JELLYFIN = {"url": "http://IP:8096", "api": "KEY", "user": "ID"}
ABS = {"url": "http://IP:8000", "api": "KEY", "lib_id": "ID"}
LOCAL_PATH = "/home/pi/music"
BOOKMARK_FILE = "bookmarks.json"


class MP3Player:
    def __init__(self):
        self.disp = LCD_1in44.LCD()
        self.disp.LCD_Init(LCD_1in44.SCAN_DIR_DFT)
        self.image = Image.new("RGB", (self.disp.width, self.disp.height), "BLACK")
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

        # Audio Setup
        self.instance = vlc.Instance("--no-video", "--network-caching=3000")
        self.player = self.instance.media_player_new()

        # Build Menu based on Toggles
        self.menu_options = []
        if FEATURES["JELLYFIN"]:
            self.menu_options.append("Jellyfin")
        if FEATURES["ABS"]:
            self.menu_options.append("Audiobookshelf")
        if FEATURES["LOCAL"]:
            self.menu_options.append("Local Files")
        if FEATURES["BT_PAIR"]:
            self.menu_options.append("Bluetooth Pair")

        self.playlist = []
        self.current_index = 0
        self.scroll_index = 0
        self.view_state = "MENU"
        self.bookmarks = self.load_bookmarks()
        self.last_save_time = time.time()

    # --- Data Methods (Modified with Toggles) ---
    def load_jellyfin(self):
        if not FEATURES["JELLYFIN"]:
            return
        url = f"{JELLYFIN['url']}/Users/{JELLYFIN['user']}/Items?IncludeItemTypes=Audio&Recursive=True&SortBy=SortName&api_key={JELLYFIN['api']}"
        try:
            r = requests.get(url, timeout=3).json()
            self.playlist = [
                {"name": i["Name"], "id": i["Id"], "source": "JELLY"}
                for i in r.get("Items", [])
            ]
            self.view_state = "BROWSER"
            self.scroll_index = 0
        except:
            self.draw_error("Jellyfin Offline")

    def load_abs(self):
        if not FEATURES["ABS"]:
            return
        headers = {"Authorization": f"Bearer {ABS['api']}"}
        url = f"{ABS['url']}/api/libraries/{ABS['lib_id']}/items"
        try:
            r = requests.get(url, headers=headers, timeout=3).json()
            self.playlist = [
                {
                    "name": i["media"]["metadata"]["title"],
                    "id": i["id"],
                    "source": "ABS",
                }
                for i in r.get("results", [])
            ]
            self.view_state = "BROWSER"
            self.scroll_index = 0
        except:
            self.draw_error("ABS Offline")

    def load_local(self):
        if not FEATURES["LOCAL"]:
            return
        try:
            files = [
                f
                for f in os.listdir(LOCAL_PATH)
                if f.lower().endswith((".mp3", ".m4a"))
            ]
            self.playlist = [
                {"name": f, "path": os.path.join(LOCAL_PATH, f), "source": "LOCAL"}
                for f in sorted(files)
            ]
            self.view_state = "BROWSER"
            self.scroll_index = 0
        except:
            self.draw_error("Local Folder Missing")

    def draw_error(self, msg):
        self.draw.rectangle((0, 0, 128, 128), fill="RED")
        self.draw.text((10, 50), "ERROR:", fill="WHITE")
        self.draw.text((10, 70), msg, fill="WHITE")
        self.disp.LCD_ShowImage(self.image, 0, 0)
        time.sleep(2)

    # --- UI and Input Handling ---
    def handle_input(self):
        # Navigation
        if self.disp.digital_read(self.disp.GPIO_KEY_UP_PIN) == 0:
            self.scroll_index = max(0, self.scroll_index - 1)
            time.sleep(0.1)
        if self.disp.digital_read(self.disp.GPIO_KEY_DOWN_PIN) == 0:
            limit = (
                len(self.menu_options)
                if self.view_state == "MENU"
                else len(self.playlist)
            )
            if limit > 0:
                self.scroll_index = min(limit - 1, self.scroll_index + 1)
            time.sleep(0.1)

        # Selection
        if (
            self.disp.digital_read(self.disp.GPIO_KEY_PRESS_PIN) == 0
            or self.disp.digital_read(self.disp.GPIO_KEY2_PIN) == 0
        ):
            if self.view_state == "MENU":
                choice = self.menu_options[self.scroll_index]
                if choice == "Jellyfin":
                    self.load_jellyfin()
                elif choice == "Audiobookshelf":
                    self.load_abs()
                elif choice == "Local Files":
                    self.load_local()
                elif choice == "Bluetooth Pair":
                    self.trigger_bt()
            elif self.view_state == "BROWSER":
                self.play_selection(self.scroll_index)
            elif self.view_state == "PLAYING":
                self.player.pause()
            time.sleep(0.3)

        # Back (Key 1)
        if self.disp.digital_read(self.disp.GPIO_KEY1_PIN) == 0:
            self.save_bookmark()
            self.view_state = "MENU"
            self.scroll_index = 0
            time.sleep(0.3)

    def trigger_bt(self):
        self.draw.rectangle((0, 0, 128, 128), fill="BLUE")
        self.draw.text((20, 50), "BT DISCOVERY ON", fill="WHITE")
        self.disp.LCD_ShowImage(self.image, 0, 0)
        os.system("bluetoothctl discoverable on && bluetoothctl pairable on")
        time.sleep(3)

    # [load_bookmarks, save_bookmark, jump_to_letter, play_selection, and render methods remain same as previous version]
    # ... (Include the rest of the helper methods from previous unified version) ...

    def load_bookmarks(self):
        if os.path.exists(BOOKMARK_FILE):
            try:
                with open(BOOKMARK_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_bookmark(self):
        if self.playlist and self.view_state == "PLAYING":
            item = self.playlist[self.current_index]
            pos = self.player.get_time()
            if pos > 0:
                self.bookmarks[item["name"]] = pos
                with open(BOOKMARK_FILE, "w") as f:
                    json.dump(self.bookmarks, f)

    def play_selection(self, index):
        self.save_bookmark()
        self.current_index = index
        item = self.playlist[index]
        if item["source"] == "LOCAL":
            uri = item["path"]
        elif item["source"] == "JELLY":
            uri = f"{JELLYFIN['url']}/Audio/{item['id']}/stream?static=true&api_key={JELLYFIN['api']}"
        elif item["source"] == "ABS":
            uri = f"{ABS['url']}/api/items/{item['id']}/play?token={ABS['api']}"
        self.player.set_media(self.instance.media_new(uri))
        self.player.play()
        time.sleep(0.6)
        if item["name"] in self.bookmarks:
            self.player.set_time(self.bookmarks[item["name"]])
        self.view_state = "PLAYING"

    def render(self):
        self.draw.rectangle((0, 0, 128, 128), fill="BLACK")
        if self.view_state == "MENU":
            self.draw.text((5, 5), "-- SOURCES --", fill="YELLOW")
            for i, opt in enumerate(self.menu_options):
                color = "WHITE" if self.scroll_index == i else "GRAY"
                self.draw.text((10, 25 + (i * 18)), opt, fill=color)
        elif self.view_state == "BROWSER":
            header = self.playlist[0]["source"] if self.playlist else "Empty"
            self.draw.text((5, 5), f"-- {header} --", fill="CYAN")
            start = max(0, self.scroll_index - 2)
            for i in range(5):
                idx = start + i
                if idx < len(self.playlist):
                    color = "WHITE" if idx == self.scroll_index else "GRAY"
                    self.draw.text(
                        (10, 25 + (i * 18)), self.playlist[idx]["name"][:15], fill=color
                    )
        elif self.view_state == "PLAYING":
            song = self.playlist[self.current_index]
            self.draw.text((5, 10), "NOW PLAYING", fill="GREEN")
            self.draw.text((5, 40), song["name"][:18], fill="WHITE")
        self.disp.LCD_ShowImage(self.image, 0, 0)

    def run(self):
        while True:
            self.handle_input()
            self.render()
            time.sleep(0.05)


if __name__ == "__main__":
    app = MP3Player()
    app.run()
