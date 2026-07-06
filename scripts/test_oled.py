#!/usr/bin/env python3
"""Hardware smoke test for the SSD1306 OLED (Phase 2 kickoff step 12).

Verification target (docs/phase2-kickoff.md): text renders on the display.

Requires I2C enabled (`sudo raspi-config nonint do_i2c 0`, then reboot --
already set on this bench, pending reboot as of Jul 5 2026) and the display
wired to the Pi's SDA/SCL pins.

    source venv/bin/activate
    python scripts/test_oled.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alerts.oled_display import OledDisplay


def main() -> None:
    print("Initializing OLED over I2C...")
    oled = OledDisplay(simulate=False)

    print("Rendering species + distance...")
    oled.show_species_distance("deer", 42)
    time.sleep(3)

    oled.clear()
    print("Done. Confirm 'DEER' and '42 m' rendered on the display.")


if __name__ == "__main__":
    main()
