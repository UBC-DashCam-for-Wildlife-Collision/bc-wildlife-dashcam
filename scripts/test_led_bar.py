#!/usr/bin/env python3
"""Hardware smoke test for the WS2812B LED bar (Phase 2 kickoff step 11).

Verification target (docs/phase2-kickoff.md): amber pulse (0.3s cycle) and
red flash (0.1s cycle) patterns visible on the bar.

Run once the LED bar is physically wired to GPIO 18 (5V power + ground +
data line, per WS2812B datasheet -- a logic-level shifter on the data line
is recommended since the Pi's GPIO is 3.3V and WS2812B expects ~5V logic).

    source venv/bin/activate
    python scripts/test_led_bar.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alerts.led_bar import LedBar

AMBER = (255, 180, 0)
RED = (255, 0, 0)


def main() -> None:
    print("Initializing LED bar on GPIO 18...")
    bar = LedBar(simulate=False)

    print("Amber pulse, cycle 300ms, 3 cycles (zone 2 pattern)...")
    bar.pulse(AMBER, cycle_ms=300, cycles=3)

    print("Red flash, cycle 100ms, 5 cycles (zone 3 pattern)...")
    bar.flash(RED, cycle_ms=100, cycles=5)

    bar.off()
    print("Done. Confirm you saw an amber pulse then a red flash.")


if __name__ == "__main__":
    main()
