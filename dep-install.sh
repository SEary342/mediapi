#!/bin/bash
set -e

echo "--- 🔄 Updating System ---"
sudo apt update && sudo apt upgrade -y

echo "--- 🔊 Installing VLC and Core Audio Libraries ---"
sudo apt install -y vlc libvlc-dev vlc-plugin-base

echo "--- ⚡ Installing Bluetooth & PipeWire Support ---"
# We swap pulseaudio for pipewire-audio and wireplumber
sudo apt install -y bluez bluetooth pipewire-audio pipewire-pulse wireplumber libspa-0.2-bluetooth

echo "--- 🛠️ Installing Python Build Essentials ---"
sudo apt install -y python3-dev build-essential libasound2-dev

echo "--- 👤 Setting Permissions ---"
# Added 'lp' group which is often required for Bluetooth communication in BlueZ
sudo usermod -aG audio $USER
sudo usermod -aG bluetooth $USER
sudo usermod -aG lp $USER

echo "--- 🐍 Installing uv for $USER ---"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$PATH"

if [ -f "pyproject.toml" ]; then
    uv sync
else
    echo "⚠️ No pyproject.toml found. Skipping uv sync."
fi

# Enable PipeWire user services for the current user
systemctl --user enable pipewire pipewire-pulse wireplumber

echo "--- ✅ Done! ---"
echo "👉 IMPORTANT: Please REBOOT your Pi now to switch to PipeWire and apply permissions."