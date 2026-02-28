"""Display rendering for LCD screen."""
from PIL import Image, ImageDraw, ImageFont
from app_config import DISPLAY_WIDTH, DISPLAY_HEIGHT


class Display:
    """Manages LCD display rendering."""

    def __init__(self, use_hardware=True):
        """Initialize display."""
        self.use_hardware = use_hardware
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT

        if use_hardware:
            import LCD_1in44

            self.disp = LCD_1in44.LCD()
            self.disp.LCD_Init(LCD_1in44.SCAN_DIR_DFT)
            self.disp.LCD_Clear()
        else:
            self.disp = None

        self.image = Image.new("RGB", (self.width, self.height), "BLACK")
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

    def clear(self):
        """Clear the display."""
        self.draw.rectangle((0, 0, self.width, self.height), fill="BLACK")

    def show_image(self, image=None):
        """Display an image."""
        img = image if image is not None else self.image
        if self.use_hardware and self.disp:
            self.disp.LCD_ShowImage(img, 0, 0)

    def draw_text(self, x, y, text, fill="WHITE"):
        """Draw text on the display."""
        self.draw.text((x, y), text, fill=fill, font=self.font)

    def draw_rectangle(self, x1, y1, x2, y2, fill=None, outline=None):
        """Draw a rectangle on the display."""
        self.draw.rectangle((x1, y1, x2, y2), fill=fill, outline=outline)

    def cleanup(self):
        """Clean up display resources."""
        if self.use_hardware and self.disp:
            self.disp.module_exit()
