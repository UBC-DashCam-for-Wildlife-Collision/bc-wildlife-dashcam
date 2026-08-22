"""
Auto-capture loop for checkerboard calibration photos (docs/car-test-2026-08-17.md
Step 3). Takes a photo every few seconds with a countdown between shots, so
whoever is holding the checkerboard just needs to reposition -- no one has to
run `rpicam-still` by hand for each of the 15-20+ photos.

The reposition cue is the physical piezo buzzer, not a terminal bell -- it
needs to be audible from outside the car with no dependence on an SSH/Termius
session staying connected (that session dropped mid-field-test on Aug 17,
see docs/car-test-2026-08-17-handoff.md). For the same reason, run this
detached so it survives a dropped connection:

    nohup python3 scripts/capture_calibration_photos.py > ~/capture_log.txt 2>&1 &
    disown

Then reconnect any time and check progress with:
    tail ~/capture_log.txt
    ls ~/calibration_photos/

Options:
    --output-dir   Where photos land (default ~/calibration_photos)
    --count        How many photos to take (default 20)
    --interval-s   Seconds between captures, to reposition the board (default 4)
    --simulate-buzzer  Print beeps instead of using GPIO (for a desk/no-hardware test run)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.alerts.buzzer import Buzzer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path.home() / "calibration_photos")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--interval-s", type=float, default=4.0)
    parser.add_argument(
        "--awb", default="daylight",
        help="White balance mode passed to rpicam-still (default 'daylight' "
        "for outdoor/through-windshield shots; use 'auto' if lighting varies).",
    )
    parser.add_argument(
        "--simulate-buzzer", action="store_true",
        help="Don't touch GPIO -- for testing this script away from the car.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    buzzer = Buzzer(simulate=args.simulate_buzzer)

    print(f"Will take {args.count} photos into {args.output_dir}, "
          f"{args.interval_s}s apart. Move/tilt/reposition the checkerboard "
          "between shots -- don't hold it flat-and-centered every time.")
    print("Listen for the buzzer, not the screen -- one short beep per countdown "
          "tick, two short beeps means a photo was just saved.")
    print("Starting in 5s... (Ctrl+C to stop early)")
    time.sleep(5)

    try:
        for i in range(1, args.count + 1):
            for remaining in (3, 2, 1):
                print(f"  {remaining}...", end=" ", flush=True)
                buzzer.beep_once()
                time.sleep(1 - 0.08)
            print()

            out_path = args.output_dir / f"photo{i:02d}.jpg"
            result = subprocess.run(
                [
                    "rpicam-still", "-o", str(out_path), "-n", "--immediate",
                    "--exposure", "sport",
                    "--awb", args.awb,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  FAILED to capture {out_path}: {result.stderr.strip()}")
                continue

            buzzer.two_short()
            print(f"  [{i}/{args.count}] saved {out_path} -- reposition now")
            if i < args.count:
                time.sleep(max(0.0, args.interval_s - 3))
    finally:
        buzzer.off()
        buzzer.cleanup()

    print(f"Done. {args.count} photos in {args.output_dir}.")
    print(f"Next: python3 scripts/calibrate_camera.py {args.output_dir} --square-size-mm 23")


if __name__ == "__main__":
    main()
