#!/bin/bash
set -e

# Identify the actual user even if running as sudo
REAL_USER="${SUDO_USER:-$(whoami)}"
REAL_HOME=$(eval echo ~$REAL_USER)

echo "--- 🔄 Updating System (as root) ---"
apt update && apt upgrade -y

echo "--- 🔌 Enabling SPI Interface ---"
# Non-interactive command to enable SPI automatically (0 = enable)
raspi-config nonint do_spi 0

echo "--- 🔊 Installing Audio & Bluetooth (PulseAudio Stack) ---"
# We explicitly install PulseAudio and remove PipeWire to prevent conflicts
apt remove --purge -y pipewire wireplumber 2>/dev/null || true
apt install -y vlc libvlc-dev vlc-plugin-base bluez bluetooth \
    pulseaudio pulseaudio-module-bluetooth \
    python3-dev build-essential libasound2-dev curl dbus-user-session \
    swig liblgpio-dev

echo "--- 👤 Setting Permissions for $REAL_USER ---"
# Added spi and gpio groups for Waveshare LCD permissions
usermod -aG audio $REAL_USER
usermod -aG bluetooth $REAL_USER
usermod -aG pulse-access $REAL_USER
usermod -aG spi $REAL_USER
usermod -aG gpio $REAL_USER

echo "--- 🐍 Installing uv for $REAL_USER ---"
if ! sudo -u "$REAL_USER" command -v uv &> /dev/null; then
    sudo -u "$REAL_USER" bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Add uv to the current shell path so the rest of the script can use it
export PATH="$REAL_HOME/.local/bin:$PATH"

if [ -f "pyproject.toml" ]; then
    echo "--- 📦 Syncing Python environment ---"
    sudo -u "$REAL_USER" bash -c "export PATH=\"$REAL_HOME/.local/bin:\$PATH\" && uv sync"
fi

echo "--- 🔊 Enabling PulseAudio User Service ---"
# Enable lingering so the user's audio daemon starts at boot
loginctl enable-linger "$REAL_USER"
USER_ID=$(id -u "$REAL_USER")
sudo -u "$REAL_USER" XDG_RUNTIME_DIR="/run/user/$USER_ID" systemctl --user enable pulseaudio.service pulseaudio.socket || true

echo "--- ✅ Dependencies Done! ---"