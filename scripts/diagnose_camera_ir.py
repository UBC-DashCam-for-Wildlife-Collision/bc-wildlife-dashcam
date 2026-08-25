#!/usr/bin/env python3
"""Diagnose whether the connected imx219 has an IR-cut filter (regular) or
not (NoIR variant) -- open question since Jul 29 2026 (CLAUDE.md hardware
table; docs/open-issues-2026-08-02.md): EXIF says "imx219", but a live
preview under indoor lighting once showed a magenta cast, which is the
classic no-IR-cut-filter symptom. That conflict is still unresolved as of
Aug 22 2026.

This script gathers two pieces of software-side evidence (neither is 100%
proof on its own -- see the printed verdict):

1. Which IPA tuning file libcamera selected. The Pi imaging stack ships
   two separate tuning files for this sensor --
   /usr/share/libcamera/ipa/rpi/pisp/imx219.json (has-IR-cut-filter tuning)
   and imx219_noir.json (no-filter tuning, different colour-correction
   matrix) -- and picks one automatically based on the module's reported
   identity. Which one it picked is themselves informative.
2. Raw sensor channel response with white balance forced to unity gains
   (--awbgains 1.0,1.0), i.e. before any auto-correction. An IR-cut filter
   blocks near-IR that would otherwise bleed into the R and B channels, so
   a filtered sensor's raw response should be G-dominant; a NoIR sensor's
   raw response tends to show elevated R/B relative to G.

For a DEFINITIVE physical test (not deducible from here): point a TV/IR
remote at the lens and press a button while recording a preview. A NoIR
sensor will show a bright flash of light that is invisible to the naked
eye; a filtered sensor will show nothing. Do that once to settle this for
good -- this script only narrows it down.
"""

import subprocess
import sys
from pathlib import Path

TUNING_DIR = Path("/usr/share/libcamera/ipa/rpi/pisp")
SCRATCH = Path("/tmp/camera_ir_diag")


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout + subprocess.run(
        cmd, capture_output=True, text=True, check=False
    ).stderr


def which_tuning_file_selected() -> str | None:
    proc = subprocess.run(
        ["rpicam-still", "-n", "-o", "/dev/null", "--width", "640", "--height", "480", "-t", "500"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in proc.stderr.splitlines():
        if "Using tuning file" in line:
            return line.strip().rsplit(" ", 1)[-1]
    return None


def capture_unity_gain_channels() -> tuple[float, float, float]:
    from PIL import Image
    import numpy as np

    SCRATCH.mkdir(exist_ok=True)
    out = SCRATCH / "unity_gain.jpg"
    subprocess.run(
        [
            "rpicam-still",
            "-n",
            "-o",
            str(out),
            "--width",
            "1640",
            "--height",
            "1232",
            "-t",
            "1500",
            "--awbgains",
            "1.0,1.0",
        ],
        capture_output=True,
        check=True,
    )
    im = np.array(Image.open(out).convert("RGB"), dtype=np.float64)
    return im[..., 0].mean(), im[..., 1].mean(), im[..., 2].mean()


def main():
    print("=== Camera IR-cut-filter diagnostic ===\n")

    available = sorted(p.name for p in TUNING_DIR.glob("imx219*.json")) if TUNING_DIR.exists() else []
    print(f"Tuning files available on this Pi: {available}")

    selected = which_tuning_file_selected()
    print(f"Tuning file libcamera selected for the connected module: {selected}\n")

    r, g, b = capture_unity_gain_channels()
    print(f"Raw sensor channel means (unity white balance, no auto-correction):")
    print(f"  R={r:.1f}  G={g:.1f}  B={b:.1f}   R/G={r / g:.3f}  B/G={b / g:.3f}")
    print("  (G-dominant -> consistent with IR-cut filter present.")
    print("   R and/or B elevated above G -> consistent with NoIR / no filter.)\n")

    verdict_filtered = selected is not None and "noir" not in selected.lower() and g > r and g > b
    print("=== Verdict ===")
    if verdict_filtered:
        print(
            "Both signals point to a STANDARD (IR-cut-filtered) imx219, not "
            "the NoIR variant. This is software-side evidence, not a physical "
            "guarantee -- confirm with the IR-remote test described in this "
            "script's module docstring if certainty matters for the report."
        )
    else:
        print(
            "Evidence is mixed or points toward NoIR -- do the IR-remote test "
            "(module docstring) before drawing a conclusion."
        )


if __name__ == "__main__":
    sys.exit(main())
