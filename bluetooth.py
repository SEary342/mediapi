"""Bluetooth pairing and connection management for PipeWire/BlueZ."""

import subprocess
import time
import logging
from storage import Storage

logger = logging.getLogger(__name__)


class BluetoothManager:
    """Manages Bluetooth device pairing and connection with PipeWire support."""

    @staticmethod
    def _run_cmd(cmd, timeout=15):
        try:
            # Combine stdout and stderr to catch all messages
            result = subprocess.run(
                cmd,
                shell=True,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            success = result.returncode == 0
            # Log the output even if it failed so we can see the "Reason: ..."
            if not success:
                logger.debug(f"Command '{cmd}' failed. Output: {result.stdout.strip()}")
            return success, result.stdout.strip(), result.stdout.strip()
        except Exception as e:
            logger.error(f"Error running command '{cmd}': {e}")
            return False, "", str(e)

    @staticmethod
    def _ensure_power():
        """Ensure the Bluetooth controller is unblocked and powered on."""
        # Unblock at the kernel level
        BluetoothManager._run_cmd("sudo rfkill unblock bluetooth")

        # Attempt to power on via bluetoothctl
        success, _, _ = BluetoothManager._run_cmd("bluetoothctl power on", timeout=5)

        if not success:
            logger.warning(
                "Standard power-on failed. Attempting hardware serial reset (hciuart)..."
            )
            BluetoothManager._run_cmd("sudo systemctl restart hciuart", timeout=10)
            time.sleep(2)
            BluetoothManager._run_cmd("bluetoothctl power on", timeout=5)

    @staticmethod
    def scan_devices(timeout_seconds=8):
        """Scan for available Bluetooth devices."""
        logger.info("Scanning for Bluetooth devices...")
        BluetoothManager._ensure_power()

        # Start discovery
        BluetoothManager._run_cmd(
            f"bluetoothctl --timeout {timeout_seconds} scan on",
            timeout=timeout_seconds + 2,
        )

        result = subprocess.run(
            ["bluetoothctl", "devices"], capture_output=True, text=True, timeout=5
        )

        devices = []
        for line in result.stdout.split("\n"):
            if line.startswith("Device"):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    devices.append({"mac": parts[1], "name": parts[2]})

        logger.info(f"Found {len(devices)} Bluetooth devices")
        return devices

    @staticmethod
    def connect(mac_address, device_name=None):
        """Pair, trust, and connect to a Bluetooth device."""
        logger.info(f"Connecting to {device_name or mac_address}...")
        BluetoothManager._ensure_power()

        # Trust (Crucial for auto-reconnect)
        logger.debug(f"Trusting {mac_address}...")
        BluetoothManager._run_cmd(f"bluetoothctl trust {mac_address}", timeout=5)

        # Pair
        logger.debug(f"Pairing with {mac_address}...")
        BluetoothManager._run_cmd(f"bluetoothctl pair {mac_address}", timeout=15)
        time.sleep(1)

        # Connect
        logger.debug(f"Initiating connection to {mac_address}...")
        success, stdout, stderr = BluetoothManager._run_cmd(
            f"bluetoothctl connect {mac_address}", timeout=15
        )

        if success:
            # Give PipeWire/WirePlumber a moment to initialize the A2DP profile
            time.sleep(2)
            # Route audio
            BluetoothManager._route_audio(mac_address)
            # Save as last-used device
            Storage.save_last_bluetooth_device(mac_address, device_name or "Unknown")
            logger.info(f"Successfully connected to {device_name or mac_address}")
            return True
        else:
            logger.error(f"Connection failed to {mac_address}: {stderr}")
            return False

    @staticmethod
    def auto_connect_last_device():
        """Attempt to auto-connect to the last-used Bluetooth device."""
        device = Storage.load_last_bluetooth_device()
        if not device:
            logger.debug("No last-used Bluetooth device found")
            return False

        logger.info(f"Attempting to auto-connect to {device['name']}...")
        BluetoothManager._ensure_power()

        try:
            # Try to connect directly (assuming already paired/trusted)
            success, _, stderr = BluetoothManager._run_cmd(
                f"bluetoothctl connect {device['mac']}", timeout=15
            )

            if success:
                time.sleep(2)
                BluetoothManager._route_audio(device["mac"])
                logger.info(f"Auto-connected to {device['name']}")
                return True
            else:
                logger.warning(f"Failed to auto-connect: {stderr}")
                return False
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")
            return False

    @staticmethod
    def _route_audio(mac_address):
        """Route PipeWire audio output with retries for slow Pi Zero CPU."""
        sink_mac = mac_address.replace(":", "_")
        max_attempts = 5

        logger.info(f"Waiting for PipeWire to initialize sink for {mac_address}...")

        for attempt in range(max_attempts):
            # Give the Pi more time to negotiate the codec (A2DP)
            time.sleep(2)

            result = subprocess.run(
                ["pactl", "list", "short", "sinks"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            sink_name = None
            for line in result.stdout.split("\n"):
                if sink_mac in line:
                    parts = line.split("\t")
                    if len(parts) > 1:
                        sink_name = parts[1]
                        break

            if sink_name:
                # Found it! Now route the audio
                BluetoothManager._run_cmd(f"pactl set-default-sink {sink_name}")
                # Move any existing audio streams to the new speaker
                move_cmd = f"pactl list short sink-inputs | cut -f1 | xargs -I{{}} pactl move-sink-input {{}} {sink_name}"
                BluetoothManager._run_cmd(move_cmd)

                # Boost volume just in case it defaulted to 0
                BluetoothManager._run_cmd(f"pactl set-sink-volume {sink_name} 70%")

                logger.info(
                    f"✅ Audio successfully routed to {sink_name} (Attempt {attempt + 1})"
                )
                return True

            logger.debug(
                f"Sink not ready yet, retrying... ({attempt + 1}/{max_attempts})"
            )

        logger.warning(
            f"❌ Connected, but no PipeWire sink appeared for {mac_address} after {max_attempts} attempts."
        )
        return False
