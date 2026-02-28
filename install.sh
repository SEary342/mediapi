#!/bin/bash
set -e

# --- 1. Identify the Real User ---
# This ensures we know who you are even though we are using sudo
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
echo "📦 Installing system packages (including build tools for lgpio)..."
sudo apt install -y vlc libvlc-dev vlc-plugin-base bluez bluetooth \
    pulseaudio pulseaudio-module-bluetooth \
    python3-dev build-essential libasound2-dev curl dbus-user-session \
    swig liblgpio-dev libcap2-bin

# --- 4. Permissions ---
echo "👤 Setting hardware permissions for $REAL_USER..."
sudo usermod -aG audio,bluetooth,pulse-access,spi,gpio "$REAL_USER"

# --- 5. Python Environment (uv) ---
echo "🐍 Setting up Python environment..."
if ! sudo -u "$REAL_USER" command -v uv &> /dev/null; then
    sudo -u "$REAL_USER" bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Ensure uv is in the path for the rest of this script
UV_PATH="$REAL_HOME/.local/bin/uv"

if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    echo "📦 Syncing Python dependencies..."
    sudo -u "$REAL_USER" bash -c "cd '$PROJECT_DIR' && export PATH=\"$REAL_HOME/.local/bin:\$PATH\" && $UV_PATH sync"
fi

# --- 6. Grant Port 80 Permission ---
echo "🔑 Granting permission for the app to use port 80..."
# This gives the Python interpreter in the venv the capability to bind to privileged ports
PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python"
if [ -f "$PYTHON_EXEC" ]; then
    sudo setcap 'cap_net_bind_service=+ep' "$PYTHON_EXEC"
    echo "✅ Permission granted to $PYTHON_EXEC"
else
    echo "⚠️  WARNING: Could not find Python executable at $PYTHON_EXEC. Skipping port permission."
fi


# --- 7. Bluetooth Configuration ---
echo "📻 Configuring Bluetooth Audio Class..."
sudo sed -i '/^#\?Enable=/c\Enable=Source,Sink,Media,Socket' /etc/bluetooth/main.conf
sudo sed -i '/^#\?Class=/c\Class=0x20041C' /etc/bluetooth/main.conf
sudo systemctl restart bluetooth

# --- 8. PulseAudio User Service (The tricky part) ---
echo "🔊 Enabling PulseAudio for $REAL_USER..."
# This ensures the user's services start even when not logged in
sudo loginctl enable-linger "$REAL_USER"

# We use 'sudo -u' to ensure the symlinks go to /home/sameary/, NOT /root/
sudo -u "$REAL_USER" XDG_RUNTIME_DIR="/run/user/$USER_ID" \
    systemctl --user enable pulseaudio.service pulseaudio.socket || true

# --- 9. Create MediAPI Service ---
echo "🔧 Creating systemd service..."
UV_EXEC="$REAL_HOME/.local/bin/uv"
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
ExecStart=$UV_EXEC run player.py
Restart=on-failure
RestartSec=10
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

# --- 10. Finalize ---
sudo systemctl daemon-reload
sudo systemctl enable mediapi.service

echo "✅ ALL DONE! PLEASE REBOOT NOW to apply group permissions and start services."