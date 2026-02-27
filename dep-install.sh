#!/bin/bash

# Exit on error
set -e

echo "--- Updating System ---"
sudo apt update && sudo apt upgrade -y

echo "--- Installing VLC and Core Audio Libraries ---"
# vlc-bin and libvlc-dev are the critical missing pieces for your error
sudo apt install -y vlc libvlc-dev vlc-plugin-base

echo "--- Installing Bluetooth & PulseAudio Support ---"
# PulseAudio is needed for reliable Bluetooth routing on a headless Pi
sudo apt install -y pulseaudio pulseaudio-module-bluetooth bluez bluetooth

echo "--- Installing Python Build Essentials ---"
# Since you're on Python 3.13, you might need these for some library compilations
sudo apt install -y python3-dev build-essential libasound2-dev

echo "--- Setting Permissions ---"
# Add your user to the audio and bluetooth groups
sudo usermod -aG audio $USER
sudo usermod -aG bluetooth $USER

echo "--- Done! ---"
echo "Please REBOOT your Pi now for group permissions and PulseAudio to initialize."