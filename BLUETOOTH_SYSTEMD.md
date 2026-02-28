# Bluetooth Auto-Connect & Systemd Guide

## What's New

### 1. **Bluetooth Auto-Connect**
The player now automatically connects to your last-used Bluetooth device on startup.

**How it works:**
- When you manually connect to a device, it's automatically saved
- On the next startup, the player attempts to reconnect
- If reconnection fails, the app continues normally (not a fatal error)

**Files involved:**
- `storage.py` - Stores device MAC and name in `bt_device.json`
- `bluetooth.py` - Handles connection logic with proper error handling
- `player.py` - Calls `BluetoothManager.auto_connect_last_device()` on startup

### 2. **Systemd Service**

Run MediAPI as a system service that starts automatically on boot.

**Benefits:**
- Starts automatically when Pi boots
- Better error handling and recovery
- Auto-connect to Bluetooth device
- Comprehensive logging
- Proper hardware permissions

## Installation (3 steps)

### Step 1: Update Service File

Edit `mediapi.service` and change these paths to match your setup:

```bash
nano mediapi.service
```

Look for and update:
```ini
WorkingDirectory=/home/pi/Code/mediapi      # Your project folder
ExecStart=/home/pi/Code/mediapi/.venv/...  # Your venv path
User=pi                                      # Your username
```

### Step 2: Install Service

```bash
# Copy service file
sudo cp mediapi.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable mediapi
sudo systemctl start mediapi
```

### Step 3: Monitor

```bash
# Check status
sudo systemctl status mediapi

# View logs in real-time
sudo journalctl -u mediapi -f

# Stop if needed
sudo systemctl stop mediapi
```

## Bluetooth Auto-Connect Behavior

| Scenario | Behavior |
|----------|----------|
| **First boot** | Service starts without auto-connect (avoids delay) |
| **After manual connection** | Device saved to `bt_device.json` |
| **Subsequent boots** | Auto-connects to saved device (if available) |
| **Connection fails** | App continues normally, shows menu |
| **Device unpaired** | Auto-connect gracefully skips and proceeds |

## Testing Before Installing Service

```bash
# Test without hardware (on any computer)
python3 -c "from player import MP3Player; app = MP3Player(use_hardware=False, auto_connect_bt=False); print('OK')"

# Test on Pi with auto-connect disabled
python3 player.py

# Check auto-connect feature
python3 test_components.py
```

## Systemd Troubleshooting

### Service won't start
```bash
# Check detailed errors
sudo journalctl -u mediapi -n 100

# Verify paths
ls -la /home/pi/Code/mediapi/.venv/bin/python
```

### Bluetooth not connecting
```bash
# Verify Bluetooth service is running
systemctl status bluetooth

# Check if device is paired
bluetoothctl devices

# Manual test
bluetoothctl connect [MAC_ADDRESS]
```

### Audio not working
```bash
# Check PulseAudio sinks
pactl list short sinks

# Verify user permissions
id pi  # Should list: spi, gpio, dialout
```

### Check logs
```bash
# Last 50 lines
sudo journalctl -u mediapi -n 50

# Only errors
sudo journalctl -u mediapi -p err

# Follow in real-time
sudo journalctl -u mediapi -f
```

## Key Changes from Previous Version

| Component | Change | Reason |
|-----------|--------|--------|
| **Bluetooth** | Uses subprocess + error handling | Works better with systemd |
| **Bluetooth** | Auto-connect to last device | Convenient for daily use |
| **Storage** | Stores BT device info | Enables auto-connect |
| **Player** | Added logging setup | Better systemd integration |
| **Service file** | Includes dependencies & permissions | Reliable startup |

## Environment Variables in Systemd

Edit the service to add or change:

```bash
# Open editor
sudo systemctl edit mediapi

# Add lines like:
[Service]
Environment="PULSE_DBUS_SERVER=unix:path=/run/pulse/dbus"
Environment="CUSTOM_VAR=value"
```

## Uninstall Service

```bash
# Stop and disable
sudo systemctl stop mediapi
sudo systemctl disable mediapi

# Remove
sudo rm /etc/systemd/system/mediapi.service
sudo systemctl daemon-reload
```

## Performance Tips

1. **Skip auto-connect if not needed:** Change `auto_connect_bt=True` to `auto_connect_bt=False` in systemd service
2. **Increase timeout if Pi is slow:** Change `TimeoutStartSec=60` to `TimeoutStartSec=120`
3. **Monitor logs:** Use `sudo journalctl -u mediapi -f` to watch startup

## Files Modified/Added

```
Modified:
  - bluetooth.py          (error handling, auto-connect, logging)
  - storage.py            (BT device persistence)
  - player.py             (logging setup, auto-connect on init)
  - api_clients.py        (added logging)

New Files:
  - mediapi.service       (systemd unit file)
  - SYSTEMD_SETUP.md      (detailed setup guide)
  - This file
```

## Quick Commands

```bash
# Start/stop/restart
sudo systemctl start mediapi
sudo systemctl stop mediapi
sudo systemctl restart mediapi

# View status
sudo systemctl status mediapi

# View all logs
sudo journalctl -u mediapi

# Test locally
python3 player.py

# Test with mock hardware
python3 -c "from player import MP3Player; MP3Player(use_hardware=False).display.draw_text(10,10,'Test'); print('OK')"
```

## Next Steps

1. Update `mediapi.service` with your paths
2. Run `sudo systemctl enable mediapi && sudo systemctl start mediapi`
3. Check status: `sudo systemctl status mediapi`
4. View logs: `sudo journalctl -u mediapi -f`
5. Connect to a Bluetooth device manually via the app
6. Device will auto-connect on next restart!

For detailed troubleshooting, see [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md)
