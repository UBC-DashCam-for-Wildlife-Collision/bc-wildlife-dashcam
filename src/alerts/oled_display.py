"""SSD1306 OLED driver, 128x64 I2C (per CLAUDE.md hardware table).

Shows species + distance in zone 3 (config/alert-zones.yaml). Requires I2C
enabled on the Pi (`sudo raspi-config nonint do_i2c 0`, then reboot) and the
display wired to the I2C pins (SDA/SCL). Verified responding at 0x3c during
the Aug 2 2026 bench test.

Layout is deliberately large and simple, not dense with information: a
driver glancing at this while approaching an animal needs the species and
distance readable instantly, not a small font packed with detail. Falls
back to PIL's tiny built-in font if DejaVu isn't present so this never
crashes over cosmetics.

`simulate=True` records calls instead of touching hardware -- see
led_bar.py docstring for why. See scripts/test_oled.py for the standalone
hardware smoke test.

The I2C connector is known to drop intermittently under vibration (bench
tests Aug 12 and Aug 22 2026: `OSError: [Errno 121] Remote I/O error` even
though `i2cdetect` shows the device present -- a full write burst fails
even when a plain bus scan succeeds). The fix that has worked so far has
been a physical reseat, but a road test can't stop to reseat a connector
mid-drive, so every I2C operation here retries with a short backoff and
degrades to a no-op on exhaustion rather than crashing the whole detection
pipeline over a non-critical display (LED + buzzer remain the primary
alert; OLED is a convenience readout).
"""

import time

WIDTH = 128
HEIGHT = 64

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SPECIES_FONT_SIZE = 18
DISTANCE_FONT_SIZE = 28

I2C_RETRY_ATTEMPTS = 3
I2C_RETRY_BACKOFF_S = 0.15


class OledDisplay:
    def __init__(self, simulate: bool = False):
        self.simulate = simulate
        self.calls: list[tuple] = []
        self._display = None
        self._draw = None
        self._image = None
        self._species_font = None
        self._distance_font = None
        self._i2c_dead = False

        if not simulate:
            import board
            import busio
            from PIL import Image, ImageDraw, ImageFont

            self._SSD1306_I2C = __import__("adafruit_ssd1306").SSD1306_I2C
            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._image = Image.new("1", (WIDTH, HEIGHT))
            self._draw = ImageDraw.Draw(self._image)
            try:
                self._species_font = ImageFont.truetype(FONT_PATH, SPECIES_FONT_SIZE)
                self._distance_font = ImageFont.truetype(FONT_PATH, DISTANCE_FONT_SIZE)
            except OSError:
                self._species_font = ImageFont.load_default()
                self._distance_font = ImageFont.load_default()
            self._connect()

    def _connect(self) -> bool:
        """(Re)initialize the SSD1306 over I2C. Returns success."""
        try:
            self._display = self._SSD1306_I2C(WIDTH, HEIGHT, self._i2c)
            self._i2c_dead = False
            return True
        except OSError as exc:
            print(f"[oled] connect failed: {exc}")
            self._display = None
            return False

    def _with_retry(self, op) -> bool:
        """Run `op()` against self._display, retrying through reconnects on
        OSError. Returns whether it eventually succeeded; never raises.
        """
        if self.simulate:
            return True
        for attempt in range(I2C_RETRY_ATTEMPTS):
            if self._display is None and not self._connect():
                time.sleep(I2C_RETRY_BACKOFF_S)
                continue
            try:
                op()
                self._i2c_dead = False
                return True
            except OSError as exc:
                print(f"[oled] I2C op failed (attempt {attempt + 1}/{I2C_RETRY_ATTEMPTS}): {exc}")
                self._display = None  # force a reconnect next attempt
                time.sleep(I2C_RETRY_BACKOFF_S)
        self._i2c_dead = True
        print("[oled] I2C unreachable -- skipping this update, LED/buzzer alerts unaffected.")
        return False

    def clear(self) -> None:
        self.calls.append(("clear",))

        def _do():
            self._display.fill(0)
            self._display.show()

        self._with_retry(_do)

    def _centered_text(self, text: str, y: int, font) -> None:
        left, top, right, bottom = self._draw.textbbox((0, 0), text, font=font)
        x = max(0, (WIDTH - (right - left)) // 2)
        self._draw.text((x, y), text, font=font, fill=255)

    def show_species_distance(self, species: str, distance_m: float) -> None:
        self.calls.append(("show_species_distance", species, distance_m))
        if self.simulate:
            return
        self._draw.rectangle((0, 0, WIDTH, HEIGHT), outline=0, fill=0)
        self._centered_text(species.upper(), 2, self._species_font)
        self._draw.line((10, 24, WIDTH - 10, 24), fill=255)
        self._centered_text(f"{distance_m:.0f} m", 32, self._distance_font)

        def _do():
            self._display.image(self._image)
            self._display.show()

        self._with_retry(_do)
