#!/bin/bash
set -e

# --- Configuration & Paths ---
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="${SUDO_USER:-$(whoami)}"
USER_HOME=$(eval echo ~$CURRENT_USER)
USER_ID=$(id -u "$CURRENT_USER")

echo "🚀 Installing MediAPI Player Service for $CURRENT_USER..."

# --- 1. Run Dependency Script ---
if [ -f "$PROJECT_DIR/dep-install.sh" ]; then
    echo "📦 Running dependency installer..."
    chmod +x "$PROJECT_DIR/dep-install.sh"
    sudo "$PROJECT_DIR/dep-install.sh"
fi

# --- 2. Find uv Executable ---
UV_PATH="$USER_HOME/.local/bin/uv"
if [ ! -f "$UV_PATH" ]; then
    UV_PATH=$(sudo -u "$CURRENT_USER" which uv)
fi

if [ -z "$UV_PATH" ]; then
    echo "❌ ERROR: Could not find uv! Please install manually."
    exit 1
fi

# --- 3. Configure Bluetooth for PulseAudio ---
echo "📻 Configuring Bluetooth Audio Class..."
sudo sed -i '/^#\?Enable=/c\Enable=Source,Sink,Media,Socket' /etc/bluetooth/main.conf
sudo sed -i '/^#\?Class=/c\Class=0x20041C' /etc/bluetooth/main.conf
sudo systemctl restart bluetooth

# --- 4. Create Systemd Service (PulseAudio Optimized) ---
echo "🔧 Creating systemd service: mediapi.service"

sudo tee /etc/systemd/system/mediapi.service > /dev/null <<EOF
[Unit]
Description=MediAPI - Music Player Service (PulseAudio)
After=network-online.target bluetooth.target sound.target pulseaudio.service
Wants=network-online.target
Requires=bluetooth.target

[Service]
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR

# Start command
ExecStart=$UV_PATH run player.py

# Restart policy
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mediapi

# PulseAudio / D-Bus Environment
# Crucial: This points VLC to the PulseAudio user socket
Environment="PULSE_SERVER=unix:/run/user/$USER_ID/pulse/native"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$USER_ID/bus"
Environment="PYTHONUNBUFFERED=1"

# Hardware Permissions (Added spi and gpio for the Waveshare LCD)
SupplementaryGroups=audio bluetooth lp spi gpio

[Install]
WantedBy=multi-user.target
EOF

# --- 5. Finalize and Start ---
sudo systemctl daemon-reload
sudo systemctl enable mediapi.service

echo "✅ Installation Complete! PLEASE REBOOT NOW."