#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo bash setup_splash.sh)"
  exit
fi

echo "--- Configuring Waveshare 1.44 LCD (ST7735S) ---"

# 1. Load modules using the modern directory
cat <<EOF > /etc/modules-load.d/waveshare_lcd.conf
spi-bcm2835
fbtft_device
EOF

# 2. Configure driver options (modern modprobe way)
# Note: speed=40MHz is stable for most Pi Zeros
cat <<EOF > /etc/modprobe.d/fbtft.conf
options fbtft_device name=adafruit18_green gpios=reset:27,dc:25,cs:8,led:24 speed=40000000 bgr=1 fps=60 rotate=180
EOF

# 3. Create a lightweight Python Splash script
# This uses Pillow to draw directly to the framebuffer (/dev/fb1)
cat <<EOF > /home/pi/splash.py
from PIL import Image, ImageDraw, ImageFont
import os

# Define screen size for Waveshare 1.44
W, H = 128, 128

try:
    # Create a black image
    img = Image.new('RGB', (W, H), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple loading message
    # You can change this to load a .png file instead: img = Image.open('logo.png')
    draw.text((20, 50), "SYSTEM STARTING", fill=(255, 255, 255))
    draw.rectangle([20, 70, 108, 80], outline=(255, 255, 255), width=1)
    draw.rectangle([22, 72, 60, 78], fill=(0, 255, 0)) # Fake progress bar
    
    # Write directly to the framebuffer
    with open('/dev/fb1', 'wb') as f:
        f.write(img.tobytes())
except Exception as e:
    print(f"Splash failed: {e}")
EOF

chown pi:pi /home/pi/splash.py

# 4. Create the Systemd Service
# 'DefaultDependencies=no' makes it run significantly earlier than standard apps
cat <<EOF > /etc/systemd/system/bootsplash.service
[Unit]
Description=Waveshare Boot Splash
DefaultDependencies=no
After=local-fs.target
Before=sysinit.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/pi/splash.py
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
EOF

# 5. Modify cmdline.txt to hide console text and map to FB1
# We append to the existing line to avoid breaking boot
if ! grep -q "fbcon=map:10" /boot/cmdline.txt; then
    sed -i 's/$/ fbcon=map:10 quiet splash logo.nologo vt.global_cursor_default=0/' /boot/cmdline.txt
    echo "Modified /boot/cmdline.txt for silent boot."
fi

# 6. Enable the service
systemctl daemon-reload
systemctl enable bootsplash.service

echo "--- Setup Complete! ---"
echo "Reboot now to see the splash screen."