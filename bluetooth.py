"""Bluetooth management optimized for PipeWire on Pi Zero."""

import subprocess
import time
import logging
from storage import Storage

logger = logging.getLogger(__name__)


class BluetoothManager:
    @staticmethod
    def _run_cmd(cmd, timeout=15):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def connect(mac_address, device_name=None):
        logger.info(f"Connecting to {device_name or mac_address}...")

        # 1. Force hardware power
        BluetoothManager._run_cmd("sudo rfkill unblock bluetooth")
        BluetoothManager._run_cmd("bluetoothctl power on")

        # 2. Connection Handshake
        BluetoothManager._run_cmd(f"bluetoothctl trust {mac_address}")
        success, output = BluetoothManager._run_cmd(
            f"bluetoothctl connect {mac_address}"
        )

        if success:
            logger.info("Bluetooth link established. Syncing audio engine...")
            # THE FIX: Give the Pi Zero's CPU time to breathe!
            time.sleep(4)

            # 3. Route Audio (Simplified)
            BluetoothManager._route_audio_aggresive()

            Storage.save_last_bluetooth_device(mac_address, device_name or "Unknown")
            return True
        else:
            logger.error(f"Link failed: {output}")
            return False

    @staticmethod
    def _route_audio_aggresive():
        """Force ANY connected BlueZ device to be the primary sink."""
        try:
            # Step A: Find the Sink Name using a broad filter
            # We look for anything starting with 'bluez_output'
            cmd = "pactl list short sinks | grep bluez_output | cut -f2"
            _, sink_name = BluetoothManager._run_cmd(cmd)

            if sink_name:
                logger.info(f"Found Bluetooth sink: {sink_name}")
                # Step B: Set as Default
                BluetoothManager._run_cmd(f"pactl set-default-sink {sink_name}")
                # Step C: Maximize Volume (PipeWire defaults to low)
                BluetoothManager._run_cmd(f"pactl set-sink-volume {sink_name} 80%")
                # Step D: Move any existing streams (VLC) to this speaker
                move_cmd = (
                    "pactl list short sink-inputs | cut -f1 | xargs -I{} pactl move-sink-input {} "
                    + sink_name
                )
                BluetoothManager._run_cmd(move_cmd)
                return True
            else:
                # HAIL MARY: If we can't find it by name, just try to 'kick' the policy
                logger.warning(
                    "Sink not found by name, attempting global policy refresh..."
                )
                BluetoothManager._run_cmd(
                    "wpctl set-default $(wpctl status | grep -m 1 'bluez_output' | grep -oP '\d+(?=\.)')"
                )
        except Exception as e:
            logger.debug(f"Routing error: {e}")
        return False

    @staticmethod
    def scan_devices(timeout_seconds=5):
        BluetoothManager._run_cmd("bluetoothctl power on")
        BluetoothManager._run_cmd(f"bluetoothctl --timeout {timeout_seconds} scan on")
        _, out = BluetoothManager._run_cmd("bluetoothctl devices")
        devices = []
        for line in out.split("\n"):
            if line.startswith("Device"):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    devices.append({"mac": parts[1], "name": parts[2]})
        return devices

    @staticmethod
    def auto_connect_last_device():
        device = Storage.load_last_bluetooth_device()
        if device:
            return BluetoothManager.connect(device["mac"], device["name"])
        return False
