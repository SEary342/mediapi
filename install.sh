#!/bin/bash
set -e

# --- 1. Identify the Real User ---
REAL_USER="${SUDO_USER:-$(whoami)}"
REAL_HOME=$(eval echo ~$REAL_USER)
USER_ID=$(id -u "$REAL_USER")
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting installation for user: $REAL_USER (ID: $USER_ID)"

# --- 2. System Updates & Hardware ---
echo "🔄 Updating system and enabling SPI..."
sudo apt update && sudo apt upgrade -y
sudo raspi-config nonint do_spi 0

# --- 3. Install Dependencies ---
echo "📦 Installing system packages..."
sudo apt install -y vlc libvlc-dev vlc-plugin-base bluez bluetooth \
    pulseaudio pulseaudio-module-bluetooth \
    python3-dev build-essential libasound2-dev curl dbus-user-session \
    swig liblgpio-dev libcap2-bin rfkill

# --- 4. Permissions ---
echo "👤 Setting hardware permissions for $REAL_USER..."
sudo usermod -aG audio,bluetooth,pulse-access,spi,gpio "$REAL_USER"

# --- 5. Python Environment (uv) ---
echo "🐍 Setting up Python environment..."
if ! sudo -u "$REAL_USER" command -v uv &> /dev/null; then
    sudo -u "$REAL_USER" bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

UV_PATH="$REAL_HOME/.local/bin/uv"

if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    echo "📦 Syncing Python dependencies..."
    sudo -u "$REAL_USER" bash -c "cd '$PROJECT_DIR' && export PATH=\"$REAL_HOME/.local/bin:\$PATH\" && $UV_PATH sync"
fi

# --- 6. Bluetooth Configuration ---
echo "📻 Configuring Bluetooth & Unblocking Radio..."
# This fixes the "Failed to set power on" error
sudo rfkill unblock bluetooth
sudo sed -i '/^#\?Enable=/c\Enable=Source,Sink,Media,Socket' /etc/bluetooth/main.conf
sudo sed -i '/^#\?Class=/c\Class=0x20041C' /etc/bluetooth/main.conf
sudo systemctl restart bluetooth

# --- 7. PulseAudio User Service ---
echo "🔊 Enabling PulseAudio for $REAL_USER..."
sudo loginctl enable-linger "$REAL_USER"
sudo -u "$REAL_USER" XDG_RUNTIME_DIR="/run/user/$USER_ID" \
    systemctl --user enable pulseaudio.service pulseaudio.socket || true

# --- 8. Create MediAPI Service ---
echo "🔧 Creating systemd service..."
# Note: We added AmbientCapabilities so the service can use Port 80 without root
sudo tee /etc/systemd/system/mediapi.service > /dev/null <<EOF
[Unit]
Description=MediAPI - Music Player Service
After=network-online.target bluetooth.target sound.target pulseaudio.service
Wants=network-online.target
Requires=bluetooth.target

[Service]
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_PATH run player.py
Restart=on-failure
RestartSec=10

# Allow Port 80 (and other privileged ports) for this non-root user
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

StandardOutput=journal
StandardError=journal
SyslogIdentifier=mediapi
Environment="PULSE_SERVER=unix:/run/user/$USER_ID/pulse/native"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$USER_ID/bus"
Environment="PYTHONUNBUFFERED=1"
SupplementaryGroups=audio bluetooth lp spi gpio

[Install]
WantedBy=multi-user.target
EOF

# --- 9. Finalize ---
sudo systemctl daemon-reload
sudo systemctl enable mediapi.service

echo "✅ ALL DONE! PLEASE REBOOT NOW."