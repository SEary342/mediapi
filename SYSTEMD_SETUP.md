# MediAPI Systemd Service Setup

This guide helps you set up MediAPI to run as a systemd service on your Raspberry Pi.

## Installation

### 1. **Prepare the Service File**

Update the paths in `mediapi.service`:

```bash
# Edit the service file
sudo nano mediapi.service
```

Change these paths to match your setup:
- `WorkingDirectory=/home/pi/Code/mediapi` (your project path)
- `ExecStart=/home/pi/Code/mediapi/.venv/bin/python` (your venv path)
- `User=pi` (your username)

### 2. **Install the Service**

```bash
# Copy to systemd directory
sudo cp mediapi.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable the service (start on boot)
sudo systemctl enable mediapi

# Start the service
sudo systemctl start mediapi
```

### 3. **Check Status**

```bash
# View service status
sudo systemctl status mediapi

# View logs
sudo journalctl -u mediapi -f    # Follow logs in real-time
sudo journalctl -u mediapi -n 50  # Last 50 log lines
```

## Configuration for Systemd

**Key settings in `mediapi.service`:**

- **`After=network-online.target bluetooth.target`** - Waits for Bluetooth to be available
- **`SupplementaryGroups=gpio spi i2c dialout`** - Access to hardware interfaces
- **`auto_connect_bt=False`** - Skips Bluetooth auto-connect on startup (can cause delays)
- **`DBUS_SYSTEM_BUS_ADDRESS`** - Allows Bluetooth communication from systemd service

## Troubleshooting

### Service Won't Start

1. **Check permissions:**
   ```bash
   ls -l /home/pi/Code/mediapi/
   # Should be readable by pi user
   ```

2. **Check venv:**
   ```bash
   /home/pi/Code/mediapi/.venv/bin/python --version
   # Should show Python version
   ```

3. **Check logs:**
   ```bash
   sudo journalctl -u mediapi -n 100 | grep -i error
   ```

### Bluetooth Not Working

1. **Verify Bluetooth is running:**
   ```bash
   systemctl status bluetooth
   ```

2. **Check if services are in correct order:**
   ```bash
   # Ensure bluetooth.service is running before mediapi
   sudo systemctl restart bluetooth
   sudo systemctl restart mediapi
   ```

3. **Manual Bluetooth test:**
   ```bash
   bluetoothctl list
   bluetoothctl devices
   ```

4. **Check permissions:**
   ```bash
   id pi  # Should show 'spi', 'gpio', 'dialout' groups
   ```

### Audio Not Working

1. **Check PulseAudio:**
   ```bash
   systemctl --user status pulseaudio
   pactl list short sinks
   ```

2. **Run as user instead of root:**
   The service MUST run as the **pi** user, not root. Verify in `mediapi.service`:
   ```
   User=pi
   Group=pi
   ```

3. **Bluetooth device not found:**
   ```bash
   pactl list short sinks | grep bluez
   ```

### High CPU Usage or Memory Issues

Check the logs for repeated connection attempts:
```bash
sudo journalctl -u mediapi -f | grep -i connect
```

Increase restart delay in `mediapi.service`:
```
RestartSec=30  # Wait 30 seconds before retry
```

## Logs

Logs are written to both:
- **Journal:** `sudo journalctl -u mediapi`
- **File:** `mediapi.log` in the working directory

Example log output:
```
2026-02-27 10:15:23,456 - __main__ - INFO - Initializing MP3 Player...
2026-02-27 10:15:24,123 - bluetooth - INFO - Attempting auto-connect to last Bluetooth device...
2026-02-27 10:15:26,789 - bluetooth - INFO - Auto-connected to JBL Speaker
```

## Management Commands

```bash
# Start/stop/restart
sudo systemctl start mediapi
sudo systemctl stop mediapi
sudo systemctl restart mediapi

# View status
sudo systemctl status mediapi

# View logs
sudo journalctl -u mediapi -f        # Real-time follow
sudo journalctl -u mediapi -n 100    # Last 100 lines
sudo journalctl -u mediapi -p err    # Only errors

# Disable auto-start on boot
sudo systemctl disable mediapi

# View service file
systemctl cat mediapi

# Edit service (auto-reloads)
sudo systemctl edit mediapi
```

## Testing Before Systemd

Before setting up the systemd service, test the application manually:

```bash
# Activate venv
source /home/pi/Code/mediapi/.venv/bin/activate

# Run with logging (test mode)
python player.py

# Check logs
tail -f mediapi.log
```

## Environment Variables

If you need additional environment variables, add them to the service file:

```ini
Environment="VAR_NAME=value"
Environment="VAR2=value2"
```

For example, to set a custom music directory:
```ini
Environment="LOCAL_MUSIC_PATH=/mnt/music"
```

## Auto-Connect Behavior

- **First boot:** Service starts without auto-connecting (to avoid delays)
- **After manual connection:** Device is saved automatically
- **Subsequent boots:** Will attempt to reconnect to previously paired device
- **If connection fails:** Service continues normally (not fatal)

## Performance Tips

1. **Disable network wait if not needed:**
   Remove `Wants=network-online.target` if you don't use remote sources

2. **Increase timeouts for slow Pi:**
   ```ini
   TimeoutStartSec=120
   ```

3. **Use socket activation** (advanced):
   Create a separate socket unit for network-based operations

4. **Monitor resource usage:**
   ```bash
   ps aux | grep mediapi
   systemctl status -l mediapi
   ```

## Uninstall

```bash
# Stop and disable
sudo systemctl stop mediapi
sudo systemctl disable mediapi

# Remove service file
sudo rm /etc/systemd/system/mediapi.service
sudo systemctl daemon-reload
```
