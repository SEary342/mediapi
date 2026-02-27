#!/bin/bash

# 1. Get the current directory and user
PROJECT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "🚀 Starting Master Installation in $PROJECT_DIR..."

# 2. Run your dependency script first
if [ -f "./dep-install.sh" ]; then
    echo "📦 Running dependency installer..."
    chmod +x dep-install.sh
    ./dep-install.sh
else
    echo "❌ Error: dep-install.sh not found. Put it in this folder!"
    exit 1
fi

# 3. Find where 'uv' is (even if it was just installed)
export PATH="$HOME/.local/bin:$PATH"
UV_PATH=$(command -v uv || echo "/home/$CURRENT_USER/.local/bin/uv")

# 4. Create the systemd service file
echo "🔧 Registering player.service with systemd..."
sudo tee /etc/systemd/system/player.service > /dev/null <<EOF
[Unit]
Description=Media Player Service
After=network.target sound.target bluetooth.target

[Service]
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_PATH run player.py
Restart=always
RestartSec=5
User=$CURRENT_USER
Group=audio
# Ensures PulseAudio/VLC logs show up in journalctl
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 5. Refresh and start
echo "🔄 Activating service..."
sudo systemctl daemon-reload
sudo systemctl enable player.service
sudo systemctl restart player.service

echo "-----------------------------------------------"
echo "✅ Done! Your player is now a system service."
echo "Check if it's running: systemctl status player.service"
echo "Read the logs: journalctl -u player.service -f"
echo "-----------------------------------------------"
echo "⚠️  Since this was a fresh install, please run: sudo reboot"