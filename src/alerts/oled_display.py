"""SSD1306 OLED driver, 128x64 I2C (per CLAUDE.md hardware table).

Shows species + distance in zone 3 (config/alert-zones.yaml). Requires I2C
enabled on the Pi (`sudo raspi-config nonint do_i2c 0`, then reboot) and the
display wired to the I2C pins (SDA/SCL) -- neither has happened on this
bench as of Jul 5 2026, so `simulate=True` is the only mode that currently
runs end-to-end here. See scripts/test_oled.py for the hardware smoke test.
"""

WIDTH = 128
HEIGHT = 64


class OledDisplay:
    def __init__(self, simulate: bool = False):
        self.simulate = simulate
        self.calls: list[tuple] = []
        self._display = None
        self._draw = None
        self._image = None

        if not simulate:
            import board
            import busio
            from adafruit_ssd1306 import SSD1306_I2C
            from PIL import Image, ImageDraw

            i2c = busio.I2C(board.SCL, board.SDA)
            self._display = SSD1306_I2C(WIDTH, HEIGHT, i2c)
            self._image = Image.new("1", (WIDTH, HEIGHT))
            self._draw = ImageDraw.Draw(self._image)

    def clear(self) -> None:
        self.calls.append(("clear",))
        if self.simulate:
            return
        self._display.fill(0)
        self._display.show()

    def show_species_distance(self, species: str, distance_m: float) -> None:
        self.calls.append(("show_species_distance", species, distance_m))
        if self.simulate:
            return
        self._draw.rectangle((0, 0, WIDTH, HEIGHT), outline=0, fill=0)
        self._draw.text((0, 0), species.upper(), fill=255)
        self._draw.text((0, 20), f"{distance_m:.0f} m", fill=255)
        self._display.image(self._image)
        self._display.show()
