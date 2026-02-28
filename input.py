"""GPIO button input handling."""

class InputManager:
    """Manages GPIO button inputs."""

    def __init__(self, use_hardware=True):
        """Initialize input manager."""
        self.use_hardware = use_hardware
        self.pins = {
            "UP": 6,
            "DOWN": 19,
            "LEFT": 5,
            "RIGHT": 26,
            "PRESS": 13,
            "KEY1": 21,
            "KEY2": 20,
            "KEY3": 16,
        }

        if use_hardware:
            import RPi.GPIO as GPIO  # ty:ignore[unresolved-import]

            self.GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            for pin in self.pins.values():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        else:
            self.GPIO = None

    def is_pressed(self, pin_name):
        """Check if a button is pressed."""
        if not self.use_hardware:
            return False

        pin = self.pins.get(pin_name)
        if pin is None:
            return False

        return self.GPIO.input(pin) == 0  # ty:ignore[unresolved-attribute]

    def cleanup(self):
        """Clean up GPIO resources."""
        if self.use_hardware and self.GPIO:
            self.GPIO.cleanup()
