#!/bin/bash
set -e

# Get absolute info
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER=$(whoami)
USER_HOME=$HOME

echo "🚀 Installing MediAPI Player Service for $CURRENT_USER..."
echo "📁 Project directory: $PROJECT_DIR"
echo "🏠 User home: $USER_HOME"

# 1. Run the dependency script
chmod +x "$PROJECT_DIR/dep-install.sh"
"$PROJECT_DIR/dep-install.sh"

# 2. Find uv executable
if command -v uv &> /dev/null; then
    UV_PATH="uv"
    echo "✓ Found uv in PATH: $(command -v uv)"
elif [ -f "$USER_HOME/.local/bin/uv" ]; then
    UV_PATH="$USER_HOME/.local/bin/uv"
    echo "✓ Found uv at: $UV_PATH"
else
    echo "❌ ERROR: Could not find uv!"
    echo "   Please ensure uv is installed: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 3. Verify Python in venv (as fallback check)
if ! [ -f "$PROJECT_DIR/.venv/bin/python" ] && ! [ -f "$PROJECT_DIR/.venv/bin/python3" ]; then
    echo "⚠️  WARNING: venv not found at $PROJECT_DIR/.venv"
    echo "   Run 'uv sync' to create it"
fi

# 4. Verify .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo "   Creating template .env file..."
    cat > "$PROJECT_DIR/.env" <<'ENVEOF'
# Jellyfin Configuration
JELLYFIN_URL=http://YOUR_JELLYFIN_SERVER:8096
JELLYFIN_API_KEY=YOUR_API_KEY
JELLYFIN_USER_ID=YOUR_USERNAME_OR_UUID

# Audiobookshelf Configuration
ABS_URL=http://YOUR_ABS_SERVER:8000
ABS_API_KEY=YOUR_API_KEY
ABS_LIB_ID=YOUR_LIB_ID
ENVEOF
    echo "   ✓ Created .env template at $PROJECT_DIR/.env"
    echo "   ⚠️  Please edit .env with your server details before starting!"
fi

# 5. Create the systemd service file
echo "🔧 Creating systemd service: mediapi.service"

sudo tee /etc/systemd/system/mediapi.service > /dev/null <<EOF
[Unit]
Description=MediAPI - Music Player Service
After=network-online.target bluetooth.target pulseaudio.service
Wants=network-online.target
Requires=bluetooth.target

[Service]
# Run as current user
User=$CURRENT_USER
Group=$CURRENT_USER

# Working directory
WorkingDirectory=$PROJECT_DIR

# Start command - use uv to run player
ExecStart=$UV_PATH run player.py

# Restart policy
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mediapi

# Set proper environment for Bluetooth/PulseAudio
Environment="DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket"
Environment="PULSE_DBUS_SERVER=unix:path=/run/pulse/dbus"
Environment="PYTHONUNBUFFERED=1"

# Allow access to hardware (GPIO, SPI, etc.)
SupplementaryGroups=gpio spi i2c dialout audio

# Device access
DevicePolicy=auto

# Type
Type=simple

# Timeouts
TimeoutStartSec=60
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. Set correct permissions on project directory
echo "🔐 Setting directory permissions..."
sudo chown -R "$CURRENT_USER:$CURRENT_USER" "$PROJECT_DIR" || true

# 7. Activate the service
echo "🔄 Reloading systemd and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable mediapi.service

# Try to start the service
if sudo systemctl start mediapi.service; then
    echo "✅ Service started successfully!"
else
    echo "⚠️  Service start had issues. Checking logs..."
fi

# 8. Show status and next steps
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Installation Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📋 Service Information:"
echo "   • Service name: mediapi"
echo "   • User: $CURRENT_USER"
echo "   • Project: $PROJECT_DIR"
echo "   • Runner: uv ($UV_PATH)"
echo ""
echo "🔍 Useful Commands:"
echo "   • Check status:  sudo systemctl status mediapi"
echo "   • View logs:     sudo journalctl -u mediapi -f"
echo "   • Stop service:  sudo systemctl stop mediapi"
echo "   • Restart:       sudo systemctl restart mediapi"
echo "   • Disable:       sudo systemctl disable mediapi"
echo ""
echo "⚙️  Configuration:"
echo "   • Edit config:   nano $PROJECT_DIR/.env"
echo "   • After changes: sudo systemctl restart mediapi"
echo ""
echo "📝 First Steps:"
echo "   1. Edit $PROJECT_DIR/.env with your server details"
echo "   2. Run: sudo systemctl restart mediapi"
echo "   3. Check logs: sudo journalctl -u mediapi -f"
echo ""