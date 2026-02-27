#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root: sudo bash $0"
  exit 1
fi

# Detect the actual user who called sudo
REAL_USER=${SUDO_USER:-$(whoami)}
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo "--- Configuring Waveshare 1.44 LCD for user: $REAL_USER ---"

# 1. Load modules using modern directories
cat <<EOF > /etc/modules-load.d/waveshare_lcd.conf
spi-bcm2835
fbtft_device
EOF

# 2. Configure driver options (ST7735S specific)
cat <<EOF > /etc/modprobe.d/fbtft.conf
options fbtft_device name=adafruit18_green gpios=reset:27,dc:25,cs:8,led:24 speed=40000000 bgr=1 fps=60 rotate=180
EOF

# 3. Create the Python Splash script in the user's home directory
SPLASH_PATH="$REAL_HOME/splash.py"

cat <<EOF > "$SPLASH_PATH"
import os
from PIL import Image, ImageDraw

# Screen dimensions for Waveshare 1.44
W, H = 128, 128

def show_splash():
    try:
        # Create image (Black background)
        img = Image.new('RGB', (W, H), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Simple graphic: Centered "LOADING" text and a bar
        draw.text((35, 50), "LOADING...", fill=(255, 255, 255))
        draw.rectangle([20, 70, 108, 80], outline=(255, 255, 255))
        draw.rectangle([22, 72, 80, 78], fill=(0, 255, 0))
        
        # Write raw pixels to the secondary framebuffer
        if os.path.exists('/dev/fb1'):
            with open('/dev/fb1', 'wb') as f:
                f.write(img.tobytes())
    except Exception as e:
        pass # Fail silently to not interrupt boot flow

if __name__ == "__main__":
    show_splash()
EOF

# Ensure the user owns their script
chown "$REAL_USER":"$REAL_USER" "$SPLASH_PATH"

# 4. Create the Systemd Service using dynamic paths
cat <<EOF > /etc/systemd/system/bootsplash.service
[Unit]
Description=Waveshare Boot Splash
DefaultDependencies=no
After=local-fs.target
Before=sysinit.target

[Service]
Type=oneshot
User=$REAL_USER
ExecStart=/usr/bin/python3 $SPLASH_PATH
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
EOF

# 5. Clean up the boot console output
# quiet: hides logs | splash: enables splash system | logo.nologo: hides the Pi berries
# vt.global_cursor_default=0: hides the blinking underscore
if ! grep -q "fbcon=map:10" /boot/cmdline.txt; then
    sed -i 's/$/ fbcon=map:10 quiet splash logo.nologo vt.global_cursor_default=0/' /boot/cmdline.txt
    echo "Modified /boot/cmdline.txt for a clean boot."
fi

# 6. Enable the service
systemctl daemon-reload
systemctl enable bootsplash.service

echo "--- Setup Complete! ---"
echo "The splash script is located at: $SPLASH_PATH"
echo "Please reboot to see the changes."