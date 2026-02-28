# MediAPI - Modular Player Architecture

This project has been refactored into modular components for easier testing and maintenance.

## Module Structure

### Core Components

- **`app_config.py`** - Application configuration loaded from environment variables (.env)
  - Feature toggles
  - Jellyfin/Audiobookshelf credentials
  - File paths and display settings

- **`storage.py`** - Bookmark persistence
  - Load/save bookmarks to JSON
  - Retrieve bookmark positions
  - Load/save last-used Bluetooth device
  - Independent of hardware

- **`api_clients.py`** - API clients for streaming services
  - `JellyfinClient` - Jellyfin server integration
  - `AudiobookshelfClient` - Audiobookshelf server integration
  - Get items and stream URIs
  - Can be mocked for testing

- **`local_library.py`** - Local file management
  - Scan music directory
  - Support for MP3, M4A, WAV formats
  - Shuffle functionality
  - Can be tested without hardware

- **`audio.py`** - VLC audio playback
  - Load and play URIs
  - Playback control (play, pause, seek)
  - Duration and position queries
  - Can be mocked for testing

### `bluetooth.py` - Bluetooth management
  - Device scanning with proper timeout handling
  - Pairing, trusting, and connection
  - Audio routing to Bluetooth sinks
  - **Auto-connect to last-used device**
  - Better error handling and logging (systemd-safe)
  - Uses subprocess instead of os.system for reliability

- **`display.py`** - LCD display rendering
  - Text and shape rendering
  - Hardware mode or mock mode
  - Initialize with `use_hardware=False` for testing

- **`input.py`** - GPIO button input handling
  - Button state checking
  - Hardware mode or mock mode
  - Initialize with `use_hardware=False` for testing

- **`player.py`** - Main orchestrator
  - Integrates all components
  - Application state management
  - UI rendering and input handling

## Testing Off the Raspberry Pi

### Quick Start

```python
from player import MP3Player

# auto_connect_bt=False skips Bluetooth startup delay
player = MP3Player(use_hardware=False, auto_connect_bte dependencies
player = MP3Player(use_hardware=False)

# Test methods without buttons or LCD
player.load_local()      # Load local files
player.render()          # Render to mock display
player.handle_input()    # Simulate input handling
```

### Run Test Examples

```bash
python test_components.py
```

This demonstrates:
- Storage operations
- Local library scanning
- API client calls
- Display rendering (mock)
- Input handling (mock)
- Full player initialization

### Individual Module Testing

**Test Storage:**
```python
from storage import Storage
storage = Storage()
bookmarks = storage.load_bookmarks()
storage.save_bookmark(bookmarks, "Song Title", 30000)
```

**Test Local Library:**
```python
from local_library import LocalLibrary
items = LocalLibrary.get_items(shuffle=False)
print([item['name'] for item in items])
```

**Test API Clients:**
```python
from api_clients import JellyfinClient
items = JellyfinClient.get_items()
uri = JellyfinClient.get_stream_uri(item_id)
```

**Test Display (Mock):**
```python
from display import Display
display = Display(use_hardware=False)
display.draw_text(10, 10, "Hello", fill="WHITE")
display.show_image()
```

**Test Input (Mock):**
```python
from input import InputManager
input_mgr = InputManager(use_hardware=False)
is_pressed = input_mgr.is_pressed("UP")  # Always False in mock mode
```

## Configuration

Create a `.env` file in the root directory:

```env
# Jellyfin Configuration
JELLYFIN_URL=http://jellyfin.internal
JELLYFIN_API_KEY=your_api_key
JELLYFIN_USER_ID=your_user_id

# Audiobookshelf Configuration
ABS_URL=http://audiobookshelf.internal
ABS_API_KEY=your_token
ABS_LIB_ID=your_lib_id
```

## Running on the Raspberry Pi

```bash
python player.py
```

The player will automatically use hardware mode when GPIO and LCD modules are available.

## Key Design Decisions

1. **Hardware Abstraction**: `Display` and `InputManager` support both hardware and mock modes
2. **API Independence**: API clients raise exceptions that are caught and displayed
3. **Stateless Utilities**: `Storage`, `LocalLibrary`, `AudioPlayer`, `Bluetooth`, and `APIClient` are mostly stateless
4. **Single Point of Control**: `MP3Player` class orchestrates all components
5. **Easy Mocking**: All dependencies injected via initialization parameters
Systemd Service

For running as a system service on the Raspberry Pi, see [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md).

Key features:
- Auto-starts on boot
- Auto-connect to previously paired Bluetooth device
- Proper hardware permissions (GPIO, SPI, I2C)
- Comprehensive logging to journal

## Logging

The application logs to both console and file:

```python
import logging
logger = logging.getLogger("mediapi")
logger.info("Application event")
logger.error("Error occurred")
```

Logs are saved to `mediapi.log` in the working directory.

For systemd:
```bash
sudo journalctl -u mediapi -f          # Follow logs in real-time
sudo journalctl -u mediapi -n 50 -p err  # Last 50 error lines
```
## Extending the Player

### Add a New Music Source

1. Create a client class in `api_clients.py`:
```python
class NewSourceClient:
    @staticmethod
    def get_items():
        # Return list of {"name": ..., "id": ..., "source": "NEWSRC"}
        pass
    
    @staticmethod
    def get_stream_uri(item_id):
        # Return stream URL
        pass
```

2. Add to `app_config.py`:
```python
FEATURES = {"NEWSRC": True, ...}
```

3. Update `player.py` to add menu option and load method

### Add New Hardware Controls

Update `input.py` with new pin names and `player.py` with input handlers.

## Debugging

Enable print statements in individual modules during testing:

```python
from local_library import LocalLibrary
import logging
logging.basicConfig(level=logging.DEBUG)

items = LocalLibrary.get_items()
```

Or use pdb:
```python
import pdb; pdb.set_trace()
```
