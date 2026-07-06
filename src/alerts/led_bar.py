"""WS2812B RGB LED bar driver, GPIO 18 (per CLAUDE.md hardware table).

Two patterns used by the alert system (config/alert-zones.yaml): amber
pulse (zone 2, cycle_ms 300) and red flash (zone 3, cycle_ms 100). Both are
blocking calls that run for a fixed duration -- callers on the Pi should run
alerts on a background thread so the GStreamer callback never blocks (see
doc/basic-pipelines.md in hailo-rpi5-examples re: callback latency).

Hardware is not wired yet (in hand, per docs/phase2-kickoff.md, but I2C/PWM
untested on this bench as of Jul 5 2026). `simulate=True` skips real
neopixel calls and just records what would have happened, so the pattern
logic is testable without hardware and the exact same code path runs once
wired -- flip the flag and run scripts/test_led_bar.py.
"""

import time

NUM_PIXELS = 8  # placeholder count; update once the bar is in hand and counted
GPIO_PIN = 18


class LedBar:
    def __init__(self, simulate: bool = False, num_pixels: int = NUM_PIXELS):
        self.simulate = simulate
        self.num_pixels = num_pixels
        self.calls: list[tuple] = []  # (action, args) log, useful in simulate mode for tests
        self._pixels = None

        if not simulate:
            import board
            import neopixel

            self._pixels = neopixel.NeoPixel(board.D18, num_pixels, auto_write=False)

    def _set_all(self, color_rgb: tuple[int, int, int]) -> None:
        self.calls.append(("set_all", color_rgb))
        if self.simulate:
            return
        self._pixels.fill(color_rgb)
        self._pixels.show()

    def off(self) -> None:
        self._set_all((0, 0, 0))

    def pulse(self, color_rgb: tuple[int, int, int], cycle_ms: int, cycles: int = 3) -> None:
        """Fade in/out. Blocking; runs `cycles` full pulses."""
        self.calls.append(("pulse", color_rgb, cycle_ms, cycles))
        if self.simulate:
            return
        steps = 20
        step_s = (cycle_ms / 1000.0) / (2 * steps)
        for _ in range(cycles):
            for i in range(steps):
                scale = i / steps
                self._pixels.fill(tuple(int(c * scale) for c in color_rgb))
                self._pixels.show()
                time.sleep(step_s)
            for i in range(steps, 0, -1):
                scale = i / steps
                self._pixels.fill(tuple(int(c * scale) for c in color_rgb))
                self._pixels.show()
                time.sleep(step_s)
        self.off()

    def flash(self, color_rgb: tuple[int, int, int], cycle_ms: int, cycles: int = 5) -> None:
        """Hard on/off flash. Blocking; runs `cycles` full flashes."""
        self.calls.append(("flash", color_rgb, cycle_ms, cycles))
        if self.simulate:
            return
        half_s = (cycle_ms / 1000.0) / 2
        for _ in range(cycles):
            self._pixels.fill(color_rgb)
            self._pixels.show()
            time.sleep(half_s)
            self._pixels.fill((0, 0, 0))
            self._pixels.show()
            time.sleep(half_s)
