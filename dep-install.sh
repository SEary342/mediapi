#!/bin/bash
set -e

# Identify the actual user even if running as sudo
REAL_USER="${SUDO_USER:-$(whoami)}"
REAL_HOME=$(eval echo ~$REAL_USER)

echo "--- 🔄 Updating System (as root) ---"
apt update && apt upgrade -y

echo "--- 🔊 Installing Audio & Bluetooth (as root) ---"
apt install -y vlc libvlc-dev vlc-plugin-base bluez bluetooth \
    pipewire-audio pipewire-pulse wireplumber libspa-0.2-bluetooth \
    python3-dev build-essential libasound2-dev curl

echo "--- 👤 Setting Permissions for $REAL_USER ---"
usermod -aG audio $REAL_USER
usermod -aG bluetooth $REAL_USER
usermod -aG lp $REAL_USER

echo "--- 🐍 Installing uv for $REAL_USER ---"
# We run the installer AS the real user
if ! sudo -u "$REAL_USER" command -v uv &> /dev/null; then
    sudo -u "$REAL_USER" bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Sync the project AS the real user
export PATH="$REAL_HOME/.local/bin:$PATH"
if [ -f "pyproject.toml" ]; then
    echo "--- 📦 Syncing Python environment ---"
    sudo -u "$REAL_USER" bash -c "export PATH=\"$REAL_HOME/.local/bin:\$PATH\" && uv sync"
fi

echo "--- 🔊 Enabling PipeWire for $REAL_USER ---"
# This fix solves the "DBUS_SESSION_BUS_ADDRESS" error
USER_ID=$(id -u "$REAL_USER")
sudo -u "$REAL_USER" XDG_RUNTIME_DIR="/run/user/$USER_ID" systemctl --user enable pipewire pipewire-pulse wireplumber || true

echo "--- ✅ Dependencies Done! ---"