import subprocess
import time
import logging
from storage import Storage

logger = logging.getLogger(__name__)


class BluetoothManager:
    @staticmethod
    def _run_cmd(cmd):
        try:
            res = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=15
            )
            return res.returncode == 0, res.stdout.strip()
        except:  # noqa: E722
            return False, ""

    @staticmethod
    def connect(mac, name=None):
        logger.info(f"Connecting to {name or mac}...")
        BluetoothManager._run_cmd("bluetoothctl power on")
        BluetoothManager._run_cmd(f"bluetoothctl trust {mac}")
        success, _ = BluetoothManager._run_cmd(f"bluetoothctl connect {mac}")

        if success:
            logger.info("Bluetooth link OK. Finding PulseAudio sink...")
            time.sleep(4)  # Allow Pi Zero CPU to process the sink
            if BluetoothManager._route_audio(mac):
                Storage.save_last_bluetooth_device(mac, name or "Unknown")
                return True
        return False

    @staticmethod
    def _route_audio(mac):
        mac_fmt = mac.replace(":", "_")
        for _ in range(5):
            _, out = BluetoothManager._run_cmd("pactl list short sinks")
            for line in out.split("\n"):
                if mac_fmt in line and "bluez_sink" in line:
                    sink = line.split("\t")[1]
                    BluetoothManager._run_cmd(f"pactl set-default-sink {sink}")
                    BluetoothManager._run_cmd(f"pactl set-sink-volume {sink} 80%")
                    logger.info(f"Audio routed to {sink}")
                    return True
            time.sleep(2)
        return False

    @staticmethod
    def scan_devices(timeout=5):
        BluetoothManager._run_cmd(f"bluetoothctl --timeout {timeout} scan on")
        _, out = BluetoothManager._run_cmd("bluetoothctl devices")
        return [
            {"mac": x.split()[1], "name": x.split(" ", 2)[2]}
            for x in out.split("\n")
            if x.startswith("Device")
        ]

    @staticmethod
    def auto_connect_last_device():
        d = Storage.load_last_bluetooth_device()
        return BluetoothManager.connect(d["mac"], d["name"]) if d else False
