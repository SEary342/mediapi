import LCD_1in44
import time
import vlc
import requests
import os
import json
from PIL import Image, ImageDraw, ImageFont

# --- Configuration (Fill these in!) ---
JELLYFIN = {"url": "http://YOUR_IP:8096", "api": "YOUR_KEY", "user": "YOUR_ID"}
ABS = {"url": "http://YOUR_IP:8000", "api": "YOUR_ABS_KEY", "lib_id": "YOUR_LIB_ID"}
LOCAL_PATH = "/home/pi/music"
BOOKMARK_FILE = "bookmarks.json"


class MP3Player:
    def __init__(self):
        # Hardware Setup
        self.disp = LCD_1in44.LCD()
        self.disp.LCD_Init(LCD_1in44.SCAN_DIR_DFT)
        self.image = Image.new("RGB", (self.disp.width, self.disp.height), "BLACK")
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

        # Audio Setup
        self.instance = vlc.Instance("--no-video", "--network-caching=3000")
        self.player = self.instance.media_player_new()

        # State Management
        self.playlist = []
        self.current_index = 0
        self.scroll_index = 0
        self.view_state = "MENU"
        self.menu_options = ["Jellyfin", "Audiobookshelf", "Local Files"]

        self.bookmarks = self.load_bookmarks()
        self.last_save_time = time.time()

    # --- Persistence Logic ---
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

    # --- Data Loading Methods ---
    def load_jellyfin(self):
        url = f"{JELLYFIN['url']}/Users/{JELLYFIN['user']}/Items?IncludeItemTypes=Audio&Recursive=True&SortBy=SortName&api_key={JELLYFIN['api']}"
        try:
            r = requests.get(url, timeout=5).json()
            self.playlist = [
                {"name": i["Name"], "id": i["Id"], "source": "JELLY"}
                for i in r.get("Items", [])
            ]
            self.view_state = "BROWSER"
            self.scroll_index = 0
        except Exception as e:
            print(f"Jellyfin Error: {e}")

    def load_abs(self):
        headers = {"Authorization": f"Bearer {ABS['api']}"}
        url = f"{ABS['url']}/api/libraries/{ABS['lib_id']}/items"
        try:
            r = requests.get(url, headers=headers, timeout=5).json()
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
        except Exception as e:
            print(f"ABS Error: {e}")

    def load_local(self):
        try:
            if not os.path.exists(LOCAL_PATH):
                os.makedirs(LOCAL_PATH)
            files = [
                f
                for f in os.listdir(LOCAL_PATH)
                if f.lower().endswith((".mp3", ".m4a", ".wav"))
            ]
            self.playlist = [
                {"name": f, "path": os.path.join(LOCAL_PATH, f), "source": "LOCAL"}
                for f in sorted(files)
            ]
            self.view_state = "BROWSER"
            self.scroll_index = 0
        except Exception as e:
            print(f"Local Error: {e}")

    def jump_to_letter(self, direction):
        if not self.playlist or self.view_state != "BROWSER":
            return
        current_char = self.playlist[self.scroll_index]["name"][0].upper()
        if direction == 1:
            for i in range(self.scroll_index + 1, len(self.playlist)):
                if self.playlist[i]["name"][0].upper() > current_char:
                    self.scroll_index = i
                    return
        else:
            for i in range(self.scroll_index - 1, -1, -1):
                if self.playlist[i]["name"][0].upper() < current_char:
                    target = self.playlist[i]["name"][0].upper()
                    while i > 0 and self.playlist[i - 1]["name"][0].upper() == target:
                        i -= 1
                    self.scroll_index = i
                    return

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

        time.sleep(0.6)  # Allow buffer
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
            src_label = self.playlist[0]["source"] if self.playlist else "Empty"
            self.draw.text((5, 5), f"-- {src_label} --", fill="CYAN")
            start = max(0, self.scroll_index - 2)
            for i in range(5):
                idx = start + i
                if idx < len(self.playlist):
                    is_bk = "*" if self.playlist[idx]["name"] in self.bookmarks else ""
                    color = "WHITE" if idx == self.scroll_index else "GRAY"
                    name = f"{is_bk}{self.playlist[idx]['name'][:14]}"
                    self.draw.text(
                        (10, 25 + (i * 18)),
                        f"> {name}" if idx == self.scroll_index else name,
                        fill=color,
                    )

        elif self.view_state == "PLAYING":
            song = self.playlist[self.current_index]
            self.draw.text((5, 10), "NOW PLAYING", fill="GREEN")
            self.draw.text((5, 35), song["name"][:18], fill="WHITE")
            # Progress Bar
            length = self.player.get_length()
            current = self.player.get_time()
            if length > 0:
                bar = int((current / length) * 110)
                self.draw.rectangle((10, 70, 120, 75), outline="WHITE")
                self.draw.rectangle((10, 70, 10 + bar, 75), fill="BLUE")

        self.disp.LCD_ShowImage(self.image, 0, 0)

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

        # Left/Right (Jump or Skip)
        if self.disp.digital_read(self.disp.GPIO_KEY_LEFT_PIN) == 0:
            if self.view_state == "BROWSER":
                self.jump_to_letter(-1)
            elif self.view_state == "PLAYING":
                self.player.set_time(self.player.get_time() - 15000)
            time.sleep(0.2)
        if self.disp.digital_read(self.disp.GPIO_KEY_RIGHT_PIN) == 0:
            if self.view_state == "BROWSER":
                self.jump_to_letter(1)
            elif self.view_state == "PLAYING":
                self.player.set_time(self.player.get_time() + 30000)
            time.sleep(0.2)

        # Selection (Center / Key 2)
        if (
            self.disp.digital_read(self.disp.GPIO_KEY_PRESS_PIN) == 0
            or self.disp.digital_read(self.disp.GPIO_KEY2_PIN) == 0
        ):
            if self.view_state == "MENU":
                if self.scroll_index == 0:
                    self.load_jellyfin()
                elif self.scroll_index == 1:
                    self.load_abs()
                elif self.scroll_index == 2:
                    self.load_local()
            elif self.view_state == "BROWSER":
                self.play_selection(self.scroll_index)
            elif self.view_state == "PLAYING":
                self.player.pause()
                self.save_bookmark()
            time.sleep(0.3)

        # Back (Key 1)
        if self.disp.digital_read(self.disp.GPIO_KEY1_PIN) == 0:
            if self.view_state == "PLAYING":
                self.save_bookmark()
            self.view_state = "MENU"
            self.scroll_index = 0
            time.sleep(0.3)

    def run(self):
        try:
            while True:
                self.handle_input()
                if (
                    self.view_state == "PLAYING"
                    and time.time() - self.last_save_time > 15
                ):
                    self.save_bookmark()
                    self.last_save_time = time.time()
                self.render()
                time.sleep(0.05)
        except KeyboardInterrupt:
            self.save_bookmark()
            self.disp.module_exit()


if __name__ == "__main__":
    app = MP3Player()
    app.run()
