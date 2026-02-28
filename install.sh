#!/bin/bash
set -e

# --- Configuration & Paths ---
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="${SUDO_USER:-$(whoami)}"
USER_HOME=$(eval echo ~$CURRENT_USER)
USER_ID=$(id -u "$CURRENT_USER")

echo "🚀 Installing MediAPI Player Service for $CURRENT_USER..."
echo "📁 Project directory: $PROJECT_DIR"
echo "🏠 User home: $USER_HOME"

# --- 1. Run Dependency Script ---
if [ -f "$PROJECT_DIR/dep-install.sh" ]; then
    echo "📦 Running dependency installer..."
    chmod +x "$PROJECT_DIR/dep-install.sh"
    "$PROJECT_DIR/dep-install.sh"
else
    echo "⚠️  WARNING: dep-install.sh not found. Skipping dependency check."
fi

# --- 2. Find uv Executable ---
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

# --- 3. Verify Python Environment ---
if [ -f "pyproject.toml" ]; then
    echo "🐍 Syncing Python environment with uv..."
    $UV_PATH sync
fi

# --- 4. Verify .env File ---
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "📝 Creating template .env file..."
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
fi

# --- 5. Create Systemd Service (PipeWire Optimized) ---
echo "🔧 Creating systemd service: mediapi.service"

sudo tee /etc/systemd/system/mediapi.service > /dev/null <<EOF
[Unit]
Description=MediAPI - Music Player Service (PipeWire)
After=network-online.target bluetooth.target sound.target
Wants=network-online.target
Requires=bluetooth.target

[Service]
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR

# Start command
ExecStart=$UV_PATH run player.py

# Restart policy
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mediapi

# PipeWire / D-Bus Environment
# We point to the user's specific PipeWire/Pulse socket
Environment="PULSE_SERVER=unix:/run/user/$USER_ID/pulse/native"
Environment="DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket"
Environment="PYTHONUNBUFFERED=1"

# Hardware Permissions
SupplementaryGroups=gpio spi i2c dialout audio bluetooth lp

[Install]
WantedBy=multi-user.target
EOF

# --- 6. Activate PipeWire User Services ---
# PipeWire MUST be running in the user session for the service to find it
echo "🔊 Ensuring PipeWire user services are enabled..."
sudo -u "$CURRENT_USER" XDG_RUNTIME_DIR="/run/user/$USER_ID" systemctl --user enable pipewire pipewire-pulse wireplumber || true

# --- 7. Finalize and Start ---
echo "🔄 Reloading systemd and enabling mediapi.service..."
sudo systemctl daemon-reload
sudo systemctl enable mediapi.service

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Installation Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📋 Important Final Steps:"
echo "   1. REBOOT your Pi now (Required for groups and PipeWire to sync)."
echo "   2. Pair your device: 'bluetoothctl trust [MAC]', then 'pair', then 'connect'."
echo "   3. Update your $PROJECT_DIR/.env with server credentials."
echo "   4. Start your player: sudo systemctl start mediapi"
echo ""
echo "🔍 Troubleshooting:"
echo "   • Check logs:  sudo journalctl -u mediapi -f"
echo "   • Check audio: pactl list sinks short"
echo "════════════════════════════════════════════════════════════"