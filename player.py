import LCD_1in44
import time
import vlc
import requests
import random
import os
import json
import subprocess
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- FEATURE TOGGLES ---
FEATURES = {"JELLYFIN": True, "ABS": True, "LOCAL": True, "BT_PAIR": True}

# --- CONFIGURATION ---
JELLYFIN = {
    "url": os.getenv("JELLYFIN_URL", "http://YOUR_IP:8096"),
    "api": os.getenv("JELLYFIN_API_KEY", "YOUR_KEY"),
    "user": os.getenv("JELLYFIN_USER_ID", "YOUR_ID"),
}
ABS = {
    "url": os.getenv("ABS_URL", "http://YOUR_IP:8000"),
    "api": os.getenv("ABS_API_KEY", "YOUR_KEY"),
    "lib_id": os.getenv("ABS_LIB_ID", "YOUR_LIB_ID"),
}
LOCAL_PATH = os.path.expanduser("~/music")
BOOKMARK_FILE = "bookmarks.json"


class MP3Player:
    def __init__(self):
        # 1. Initialize LCD Hardware
        self.disp = LCD_1in44.LCD()
        self.disp.LCD_Init(LCD_1in44.SCAN_DIR_DFT)
        self.disp.LCD_Clear()
        self.image = Image.new("RGB", (self.disp.width, self.disp.height), "BLACK")
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

        # 2. Setup GPIO Buttons
        GPIO.setmode(GPIO.BCM)
        self.pins = {
            "UP": 6,
            "DOWN": 19,
            "LEFT": 5,
            "RIGHT": 26,
            "PRESS": 13,
            "KEY1": 21,
            "KEY2": 20,
            "KEY3": 16,
        }
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # 3. Audio Setup (Forcing PulseAudio/PipeWire output)
        self.instance = vlc.Instance(
            "--no-video", "--network-caching=3000", "--aout=pulse"
        )
        self.player = self.instance.media_player_new()

        # 4. App State
        self.playlist = []
        self.bt_devices = []
        self.current_index = 0
        self.scroll_index = 0
        self.view_state = "MENU"
        self.menu_options = []
        if FEATURES["JELLYFIN"]:
            self.menu_options.append("Jellyfin")
        if FEATURES["ABS"]:
            self.menu_options.append("Audiobookshelf")
        if FEATURES["LOCAL"]:
            self.menu_options.extend(["Local Files", "Local Shuffle"])
        if FEATURES["BT_PAIR"]:
            self.menu_options.append("Bluetooth Pair")

        self.bookmarks = self.load_bookmarks()
        self.last_save_time = time.time()

    # --- Persistence & Loaders (Abbreviated for brevity, remains same as previous) ---
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

    def load_jellyfin(self):
        url = f"{JELLYFIN['url']}/Users/{JELLYFIN['user']}/Items?IncludeItemTypes=Audio&Recursive=True&SortBy=SortName&api_key={JELLYFIN['api']}"
        try:
            r = requests.get(url, timeout=4).json()
            self.playlist = [
                {"name": i["Name"], "id": i["Id"], "source": "JELLY"}
                for i in r.get("Items", [])
            ]
            self.view_state, self.scroll_index = "BROWSER", 0
        except:
            self.draw_error("Jellyfin Fail")

    def load_abs(self):
        headers = {"Authorization": f"Bearer {ABS['api']}"}
        url = f"{ABS['url']}/api/libraries/{ABS['lib_id']}/items"
        try:
            r = requests.get(url, headers=headers, timeout=4).json()
            self.playlist = [
                {
                    "name": i["media"]["metadata"]["title"],
                    "id": i["id"],
                    "source": "ABS",
                }
                for i in r.get("results", [])
            ]
            self.view_state, self.scroll_index = "BROWSER", 0
        except:
            self.draw_error("ABS Fail")

    def load_local(self, shuffle=False):
        if not os.path.exists(LOCAL_PATH):
            os.makedirs(LOCAL_PATH)
        files = [
            f
            for f in os.listdir(LOCAL_PATH)
            if f.lower().endswith((".mp3", ".m4a", ".wav"))
        ]
        if not files:
            self.draw_error("No Local Files")
            return
        self.playlist = [
            {"name": f, "path": os.path.join(LOCAL_PATH, f), "source": "LOCAL"}
            for f in sorted(files)
        ]
        if shuffle:
            random.shuffle(self.playlist)
            self.play_selection(0)
        else:
            self.view_state, self.scroll_index = "BROWSER", 0

    def jump_to_letter(self, direction):
        if not self.playlist or self.view_state != "BROWSER":
            return
        curr = self.playlist[self.scroll_index]["name"][0].upper()
        if direction == 1:
            for i in range(self.scroll_index + 1, len(self.playlist)):
                if self.playlist[i]["name"][0].upper() > curr:
                    self.scroll_index = i
                    return
        else:
            for i in range(self.scroll_index - 1, -1, -1):
                if self.playlist[i]["name"][0].upper() < curr:
                    t = self.playlist[i]["name"][0].upper()
                    while i > 0 and self.playlist[i - 1]["name"][0].upper() == t:
                        i -= 1
                    self.scroll_index = i
                    return

    def play_selection(self, index):
        self.save_bookmark()
        self.current_index = index
        item = self.playlist[index]
        uri = item["path"] if item["source"] == "LOCAL" else ""
        if item["source"] == "JELLY":
            uri = f"{JELLYFIN['url']}/Audio/{item['id']}/stream?static=true&api_key={JELLYFIN['api']}"
        if item["source"] == "ABS":
            uri = f"{ABS['url']}/api/items/{item['id']}/play?token={ABS['api']}"

        self.player.set_media(self.instance.media_new(uri))
        self.player.play()
        time.sleep(0.6)
        if item["name"] in self.bookmarks:
            self.player.set_time(self.bookmarks[item["name"]])
        self.view_state = "PLAYING"

    # --- Bluetooth Logic ---
    def draw_message(self, title, msg, color="BLUE"):
        self.draw.rectangle((0, 0, 128, 128), fill=color)
        self.draw.text((10, 45), title, fill="WHITE")
        self.draw.text((10, 65), msg[:18], fill="WHITE")
        self.disp.LCD_ShowImage(self.image, 0, 0)

    def scan_bluetooth(self):
        self.draw_message("BLUETOOTH", "Scanning (5s)...")
        os.system("bluetoothctl power on")
        os.system("bluetoothctl --timeout 5 scan on")
        result = subprocess.run(
            ["bluetoothctl", "devices"], capture_output=True, text=True
        )
        devices = []
        for line in result.stdout.split("\n"):
            if line.startswith("Device"):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    devices.append({"mac": parts[1], "name": parts[2]})

        if not devices:
            self.draw_error("No BT Devices")
            self.view_state = "MENU"
        else:
            self.bt_devices = devices
            self.view_state, self.scroll_index = "BT_SCAN", 0

    def connect_bluetooth(self, index):
        device = self.bt_devices[index]
        mac = device["mac"]
        self.draw_message("CONNECTING", device["name"])

        # Connection sequence
        os.system(f"bluetoothctl pair {mac}")
        time.sleep(1)
        os.system(f"bluetoothctl trust {mac}")
        time.sleep(1)
        os.system(f"bluetoothctl connect {mac}")
        time.sleep(2)  # Wait for Pulse/Pipewire to recognize the new sink

        # --- ROUTING AUDIO ---
        # Look for the new bluetooth sink and set it as default
        try:
            # Find the sink name that contains the MAC address (formatted with underscores)
            sink_mac = mac.replace(":", "_")
            result = subprocess.run(
                ["pactl", "list", "short", "sinks"], capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if sink_mac in line:
                    sink_name = line.split("\t")[1]
                    os.system(f"pactl set-default-sink {sink_name}")
                    # Move currently playing stream to the new sink (if playing)
                    os.system(
                        f"pactl list short sink-inputs | cut -f1 | xargs -I{{}} pactl move-sink-input {{}} {sink_name}"
                    )
                    break
        except:
            pass

        self.draw_message("SUCCESS", "Audio Routed!", color="GREEN")
        time.sleep(2)
        self.view_state, self.scroll_index = "MENU", 0

    # --- UI Rendering & Input (Standard logic with BT_SCAN state added) ---
    def draw_error(self, msg):
        self.draw.rectangle((0, 0, 128, 128), fill="RED")
        self.draw.text((10, 50), "ERROR:", fill="WHITE")
        self.draw.text((10, 70), msg, fill="WHITE")
        self.disp.LCD_ShowImage(self.image, 0, 0)
        time.sleep(2)

    def render(self):
        self.draw.rectangle((0, 0, 128, 128), fill="BLACK")
        if self.view_state == "MENU":
            self.draw.text((5, 5), "-- SOURCES --", fill="YELLOW")
            for i, opt in enumerate(self.menu_options):
                color = "WHITE" if self.scroll_index == i else "GRAY"
                self.draw.text((10, 25 + (i * 18)), opt, fill=color)
        elif self.view_state == "BROWSER":
            src = self.playlist[0]["source"] if self.playlist else ""
            self.draw.text((5, 5), f"-- {src} --", fill="CYAN")
            start = max(0, self.scroll_index - 2)
            for i in range(5):
                idx = start + i
                if idx < len(self.playlist):
                    is_bk = "*" if self.playlist[idx]["name"] in self.bookmarks else ""
                    color = "WHITE" if idx == self.scroll_index else "GRAY"
                    self.draw.text(
                        (10, 25 + (i * 18)),
                        f"{is_bk}{self.playlist[idx]['name'][:14]}",
                        fill=color,
                    )
        elif self.view_state == "BT_SCAN":
            self.draw.text((5, 5), "-- DEVICES --", fill="MAGENTA")
            start = max(0, self.scroll_index - 2)
            for i in range(5):
                idx = start + i
                if idx < len(self.bt_devices):
                    color = "WHITE" if idx == self.scroll_index else "GRAY"
                    self.draw.text(
                        (10, 25 + (i * 18)),
                        self.bt_devices[idx]["name"][:14],
                        fill=color,
                    )
        elif self.view_state == "PLAYING":
            song = self.playlist[self.current_index]
            self.draw.text((5, 10), "NOW PLAYING", fill="GREEN")
            self.draw.text((5, 40), song["name"][:18], fill="WHITE")
            length, cur = self.player.get_length(), self.player.get_time()
            if length > 0:
                bar = int((cur / length) * 110)
                self.draw.rectangle((10, 75, 120, 80), outline="WHITE")
                self.draw.rectangle((10, 75, 10 + bar, 80), fill="BLUE")
        self.disp.LCD_ShowImage(self.image, 0, 0)

    def handle_input(self):
        # UP/DOWN Navigation
        if GPIO.input(self.pins["UP"]) == 0:
            self.scroll_index = max(0, self.scroll_index - 1)
            time.sleep(0.15)
        if GPIO.input(self.pins["DOWN"]) == 0:
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

        # SELECTION
        if GPIO.input(self.pins["PRESS"]) == 0 or GPIO.input(self.pins["KEY2"]) == 0:
            if self.view_state == "MENU":
                choice = self.menu_options[self.scroll_index]
                if "Jellyfin" in choice:
                    self.load_jellyfin()
                elif "Audiobook" in choice:
                    self.load_abs()
                elif "Local Files" in choice:
                    self.load_local(False)
                elif "Shuffle" in choice:
                    self.load_local(True)
                elif "Bluetooth" in choice:
                    self.scan_bluetooth()
            elif self.view_state == "BROWSER":
                self.play_selection(self.scroll_index)
            elif self.view_state == "BT_SCAN":
                self.connect_bluetooth(self.scroll_index)
            elif self.view_state == "PLAYING":
                self.player.pause()
                self.save_bookmark()
            time.sleep(0.3)

        # BACK
        if GPIO.input(self.pins["KEY1"]) == 0:
            self.save_bookmark()
            self.view_state, self.scroll_index = "MENU", 0
            time.sleep(0.3)

        # LEFT/RIGHT (Skip/Letter Jump)
        if GPIO.input(self.pins["LEFT"]) == 0:
            if self.view_state == "BROWSER":
                self.jump_to_letter(-1)
            elif self.view_state == "PLAYING":
                self.player.set_time(max(0, self.player.get_time() - 15000))
            time.sleep(0.2)
        if GPIO.input(self.pins["RIGHT"]) == 0:
            if self.view_state == "BROWSER":
                self.jump_to_letter(1)
            elif self.view_state == "PLAYING":
                self.player.set_time(self.player.get_time() + 30000)
            time.sleep(0.2)

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
            GPIO.cleanup()
            self.disp.module_exit()


if __name__ == "__main__":
    app = MP3Player()
    app.run()
