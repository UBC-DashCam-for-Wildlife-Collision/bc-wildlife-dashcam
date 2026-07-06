"""Active piezo buzzer driver, GPIO (per CLAUDE.md hardware table).

Two patterns from config/alert-zones.yaml: "two-short" (zone 2) and
"continuous-rapid" (zone 3). Active buzzers only need on/off, not a PWM
tone, since they generate their own tone internally.

`simulate=True` records calls instead of touching GPIO -- see led_bar.py
docstring for why. Pin number is a placeholder; confirm against the actual
wiring once Aditya/Deepansh connect it (not yet documented in
interface_contract.md as of Jul 5 2026 -- only the LED pin (GPIO 18) and GPS
UART pin (GPIO 15) are nailed down there).
"""

import time

BUZZER_PIN = 17  # placeholder -- confirm against actual wiring before hardware test


class Buzzer:
    def __init__(self, simulate: bool = False, pin: int = BUZZER_PIN):
        self.simulate = simulate
        self.pin = pin
        self.calls: list[tuple] = []
        self._gpio = None

        if not simulate:
            import RPi.GPIO as GPIO

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO

    def _set(self, on: bool) -> None:
        if self.simulate:
            return
        self._gpio.output(self.pin, self._gpio.HIGH if on else self._gpio.LOW)

    def off(self) -> None:
        self.calls.append(("off",))
        self._set(False)

    def two_short(self, beep_s: float = 0.15, gap_s: float = 0.15) -> None:
        """Two short beeps -- zone 2 pattern."""
        self.calls.append(("two_short", beep_s, gap_s))
        if self.simulate:
            return
        for _ in range(2):
            self._set(True)
            time.sleep(beep_s)
            self._set(False)
            time.sleep(gap_s)

    def continuous_rapid(self, duration_s: float = 1.0, beep_s: float = 0.08, gap_s: float = 0.05) -> None:
        """Rapid continuous beeping -- zone 3 pattern. Blocking for `duration_s`."""
        self.calls.append(("continuous_rapid", duration_s, beep_s, gap_s))
        if self.simulate:
            return
        elapsed = 0.0
        while elapsed < duration_s:
            self._set(True)
            time.sleep(beep_s)
            self._set(False)
            time.sleep(gap_s)
            elapsed += beep_s + gap_s

    def cleanup(self) -> None:
        if not self.simulate and self._gpio is not None:
            self._gpio.cleanup(self.pin)
