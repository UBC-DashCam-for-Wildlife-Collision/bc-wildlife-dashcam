#!/usr/bin/env python3
"""Hardware smoke test for the piezo buzzer (Phase 2 kickoff step 13).

Verification target (docs/phase2-kickoff.md): two-short-beep and
continuous-rapid patterns audible.

Run once the buzzer is wired (see src/alerts/buzzer.py BUZZER_PIN --
confirm the actual GPIO pin before running; it's a placeholder until wired).

    source venv/bin/activate
    python scripts/test_buzzer.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alerts.buzzer import Buzzer


def main() -> None:
    print("Initializing buzzer...")
    buzzer = Buzzer(simulate=False)

    print("Two-short-beep pattern (zone 2)...")
    buzzer.two_short()
    time.sleep(1)

    print("Continuous-rapid pattern, 1s (zone 3)...")
    buzzer.continuous_rapid(duration_s=1.0)

    buzzer.off()
    buzzer.cleanup()
    print("Done. Confirm you heard two short beeps, then rapid continuous beeping.")


if __name__ == "__main__":
    main()
