#!/bin/bash
set -e

# Get absolute info
PROJECT_DIR=$(pwd)
CURRENT_USER=$(whoami)
USER_HOME=$HOME

echo "🚀 Installing Media Player Service for $CURRENT_USER..."

# 1. Run the dependency script
chmod +x dep-install.sh
./dep-install.sh

# 2. Define the exact UV path
# We hardcode the home path here to prevent systemd path-resolve issues
UV_PATH="$USER_HOME/.local/bin/uv"

echo "🔧 Creating systemd service with path: $UV_PATH"

# 3. Create the service file
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
Environment=PYTHONUNBUFFERED=1
# Important for local uv installations:
Environment=PATH=$USER_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

# 4. Final Activation
echo "🔄 Reloading and starting..."
sudo systemctl unmask player.service
sudo systemctl daemon-reload
sudo systemctl enable player.service
sudo systemctl restart player.service

echo "✅ Installation Complete! Check logs with: journalctl -u player.service -f"