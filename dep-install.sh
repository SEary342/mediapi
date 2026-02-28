#!/bin/bash

# Exit on error
set -e

echo "--- 🔄 Updating System ---"
sudo apt update && sudo apt upgrade -y

echo "--- 🔊 Installing VLC and Core Audio Libraries ---"
# vlc-bin and libvlc-dev are the critical pieces for your player
sudo apt install -y vlc libvlc-dev vlc-plugin-base

echo "--- ⚡ Installing Bluetooth & PulseAudio Support ---"
sudo apt install -y pulseaudio pulseaudio-module-bluetooth bluez bluetooth pipewire-audio

echo "--- 🛠️ Installing Python Build Essentials ---"
sudo apt install -y python3-dev build-essential libasound2-dev

echo "--- 👤 Setting Permissions ---"
sudo usermod -aG audio $USER
sudo usermod -aG bluetooth $USER

echo "--- 🐍 Installing uv for $USER ---"
# Force install uv as the current user, not root
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Ensure the local bin is in the current script's path
export PATH="$HOME/.local/bin:$PATH"

# Sync the project (installs what's in your pyproject.toml)
if [ -f "pyproject.toml" ]; then
    uv sync
else
    echo "⚠️ No pyproject.toml found. Skipping uv sync."
fi

echo "--- ✅ Done! ---"
echo "👉 IMPORTANT: Please REBOOT your Pi now for audio/bluetooth permissions to take effect."