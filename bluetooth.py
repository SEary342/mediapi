"""Bluetooth pairing and connection management."""
import subprocess
import time
import logging
from storage import Storage

logger = logging.getLogger(__name__)


class BluetoothManager:
    """Manages Bluetooth device pairing and connection."""

    @staticmethod
    def _run_cmd(cmd, timeout=10):
        """Run a shell command safely, returns (success, output, error)."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                timeout=timeout,
                capture_output=True,
                text=True,
            )
            success = result.returncode == 0
            if not success and result.stderr:
                logger.debug(f"Command '{cmd}' failed with: {result.stderr.strip()}")
            return success, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.debug(f"Command '{cmd}' timed out after {timeout}s")
            return False, "", f"Timeout after {timeout}s"
        except Exception as e:
            logger.error(f"Error running command '{cmd}': {e}")
            return False, "", str(e)

    @staticmethod
    def scan_devices(timeout_seconds=5):
        """Scan for available Bluetooth devices."""
        logger.info("Scanning for Bluetooth devices...")
        BluetoothManager._run_cmd("bluetoothctl power on", timeout=5)
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
        """Pair and connect to a Bluetooth device."""
        logger.info(f"Connecting to {device_name or mac_address}...")

        # Pair
        logger.debug(f"Pairing with {mac_address}...")
        success, stdout, stderr = BluetoothManager._run_cmd(
            f"bluetoothctl pair {mac_address}", timeout=15
        )
        if not success and stderr:
            logger.warning(f"Pairing result: {stderr}")
        time.sleep(1)

        # Trust
        logger.debug(f"Trusting {mac_address}...")
        success, stdout, stderr = BluetoothManager._run_cmd(
            f"bluetoothctl trust {mac_address}", timeout=5
        )
        if not success and stderr:
            logger.warning(f"Trust result: {stderr}")
        time.sleep(1)

        # Connect
        logger.debug(f"Initiating connection to {mac_address}...")
        success, stdout, stderr = BluetoothManager._run_cmd(
            f"bluetoothctl connect {mac_address}", timeout=15
        )
        if not success:
            if stderr:
                logger.error(f"Connection failed: {stderr}")
            else:
                logger.error("Connection failed (no error details)")
            return False
        
        time.sleep(2)

        if success:
            # Route audio
            BluetoothManager._route_audio(mac_address)
            # Save as last-used device
            Storage.save_last_bluetooth_device(mac_address, device_name or "Unknown")
            logger.info(f"Successfully connected to {device_name or mac_address}")
            return True
        else:
            logger.error(f"Failed to connect to {mac_address}")
            return False

    @staticmethod
    def auto_connect_last_device():
        """Attempt to auto-connect to the last-used Bluetooth device."""
        device = Storage.load_last_bluetooth_device()
        if not device:
            logger.debug("No last-used Bluetooth device found")
            return False

        logger.info(f"Attempting to auto-connect to {device['name']}...")
        try:
            # Check if device is available
            result = subprocess.run(
                ["bluetoothctl", "devices"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if device["mac"] not in result.stdout:
                logger.warning(
                    f"Last device {device['mac']} not available, skipping auto-connect"
                )
                return False

            # Try to connect
            success, stdout, stderr = BluetoothManager._run_cmd(
                f"bluetoothctl connect {device['mac']}", timeout=10
            )
            time.sleep(2)

            if success:
                BluetoothManager._route_audio(device["mac"])
                logger.info(f"Auto-connected to {device['name']}")
                return True
            else:
                logger.warning(f"Failed to auto-connect to {device['name']}")
                return False
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")
            return False

    @staticmethod
    def _route_audio(mac_address):
        """Route audio output to the connected Bluetooth device."""
        try:
            sink_mac = mac_address.replace(":", "_")
            result = subprocess.run(
                ["pactl", "list", "short", "sinks"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.split("\n"):
                if sink_mac in line:
                    sink_name = line.split("\t")[1]
                    logger.debug(f"Routing audio to sink: {sink_name}")
                    success, _, stderr = BluetoothManager._run_cmd(
                        f"pactl set-default-sink {sink_name}", timeout=5
                    )
                    if not success and stderr:
                        logger.warning(f"Failed to set default sink: {stderr}")
                    # Move currently playing stream to the new sink (if playing)
                    success, _, stderr = BluetoothManager._run_cmd(
                        f"pactl list short sink-inputs | cut -f1 | xargs -I{{}} pactl move-sink-input {{}} {sink_name}",
                        timeout=5,
                    )
                    if not success and stderr:
                        logger.warning(f"Failed to move sink inputs: {stderr}")
                    logger.info(f"Audio routed to {sink_name}")
                    break
        except subprocess.TimeoutExpired:
            logger.warning("Audio routing timed out")
        except Exception as e:
            logger.warning(f"Failed to route audio: {e}")

