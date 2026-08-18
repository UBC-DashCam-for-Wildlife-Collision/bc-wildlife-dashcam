"""
Auto-capture loop for checkerboard calibration photos (docs/car-test-2026-08-17.md
Step 3). Takes a photo every few seconds with a countdown between shots, so
whoever is holding the checkerboard just needs to reposition -- no one has to
run `rpicam-still` by hand for each of the 15-20+ photos.

Run:
    python3 scripts/capture_calibration_photos.py

Options:
    --output-dir   Where photos land (default ~/calibration_photos)
    --count        How many photos to take (default 20)
    --interval-s   Seconds between captures, to reposition the board (default 4)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


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
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Will take {args.count} photos into {args.output_dir}, "
          f"{args.interval_s}s apart. Move/tilt/reposition the checkerboard "
          "between shots -- don't hold it flat-and-centered every time.")
    print("Starting in 5s... (Ctrl+C to stop early)")
    time.sleep(5)

    for i in range(1, args.count + 1):
        for remaining in (3, 2, 1):
            print(f"  {remaining}...", end=" ", flush=True)
            sys.stdout.write("\a")  # terminal bell -- audible cue, no buzzer hardware needed
            sys.stdout.flush()
            time.sleep(1)
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

        print(f"  [{i}/{args.count}] saved {out_path} -- reposition now")
        if i < args.count:
            time.sleep(max(0.0, args.interval_s - 3))

    print(f"Done. {args.count} photos in {args.output_dir}.")
    print(f"Next: python3 scripts/calibrate_camera.py {args.output_dir} --square-size-mm 23")


if __name__ == "__main__":
    main()
