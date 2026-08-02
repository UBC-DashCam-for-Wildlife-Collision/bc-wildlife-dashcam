# Open Issues — Pi Camera/Detection Integration Session (Aug 2, 2026)

For Claude Code on the Mac. Found today while reconnecting the camera and
wiring the compiled `.hef` into the live detection pipeline on the Pi
(`scripts/run_wildlife_detection.py`, committed this session). Ranked by
how actionable each is from the Mac side.

## 1. [BLOCKING, Mac-actionable] Label index convention is unverified

`config/hailo_labels.json` (committed on the Pi this session) assumes
Hailo's usual convention: index 0 = `"unlabeled"`, then the 7 species
1-indexed after it —

```
0 unlabeled, 1 bear, 2 cougar, 3 coyote, 4 deer, 5 elk, 6 moose, 7 raccoon
```

This was inferred from the only reference example available on the Pi
(`hailo-rpi5-examples/local_resources/barcode-labels.json`), **not** from
the actual compile config. The real `nms_postprocess` JSON + model script
(`.alls`) that defined `"classes": 7` for `bc_dashcam_yolov8n.hef` was
built in the Colab session per `docs/meeting_log.md` (Jul 29-30 entry) and
was never committed to this repo — it's presumably still on Drive
(`bc-dashcam/run1_7class/weights/`) or in Colab scratch space.

Ran two dry-run tests on the Pi (stock sample video, then the live camera
pointed at an indoor workbench scene) — pipeline ran end-to-end with no
crashes, and produced varied species labels/confidences, but since neither
scene contains real wildlife this is **inconclusive** on whether indexing
is correct. A silent off-by-one here would mean every real detection is
mislabeled as the adjacent species alphabetically.

**Action:** retrieve the actual `nms_postprocess`/`.alls` config from
Drive/Colab, commit it to this repo (e.g. `models/bc_dashcam_yolov8n.alls`
or alongside in `docs/`), and confirm directly whether the class-id
convention matches what `config/hailo_labels.json` on the Pi assumes.
Correct `config/hailo_labels.json` if not — that file needs a `git pull`
on the Pi afterward either way.

## 2. [Not Mac-fixable, for awareness] Camera identity is contradictory

Earlier this session CLAUDE.md's hardware table was updated to say the
connected camera is "not the Module 3 NoIR" based on `rpicam-still` EXIF
showing `Model: imx219` — but EXIF's model tag can't actually distinguish
the NoIR and standard variants (same sensor chip, different lens filter).

A later live-preview shot under indoor fluorescent lighting showed a
**strong magenta/pink color cast** — a classic symptom of *no* IR-cut
filter, i.e. evidence pointing the other way (this **is** the NoIR
variant after all). The two pieces of evidence conflict, and the CLAUDE.md
edit from earlier today may be wrong.

**Action:** none possible from Mac — this needs either a physical check
(the module usually has "NoIR" printed on it) or a controlled test (point
an IR remote at it while pressing a button; NoIR sensors show the IR LED
as a bright dot, standard sensors show nothing). Flag this in whatever
report/limitations section discusses the camera, and don't treat either
of today's CLAUDE.md notes on this as settled.

## 3. [Not Mac-fixable directly, but prep possible] No real camera calibration

`scripts/run_wildlife_detection.py` uses a hardcoded
`FOCAL_LENGTH_PX_PLACEHOLDER = 1000.0` — not a real value. All
distance/zone output from the live pipeline is currently meaningless.
This depends on Aditya's OpenCV checkerboard calibration
(`camera_matrix.npy`, `dist_coeffs.npy` per `docs/interface_contract.md`
section 2), which hasn't happened yet.

**Action:** can't calibrate without the physical checkerboard + camera
session, but Mac Claude could pre-write the calibration analysis script
(checkerboard corner detection → `camera_matrix.npy`/`dist_coeffs.npy` →
extract focal length in px) now, so it's ready to run the moment
calibration photos exist, rather than starting from scratch later.

## 4. [Already tracked] mAP drop + max-optimization compile still deferred

Not new today, just repeating the pointer since it's the reason #1 can't
be fully validated yet: `docs/hailo-quantization-checklist.md` step 4
(float32-vs-INT8 mAP measurement) and `docs/meeting_log.md`'s "Not
done/deferred" section (max-optimization compile interrupted twice by
Colab disconnects) are both still open. The `.hef` on the Pi right now is
the plain (non-max) compile.

## 5. [Low priority] Stray files in the Pi's working tree

`hailort.log`, `reboot.save`, `reboot.save.1` show up untracked in the
Pi's git status (pre-dating this session, never committed/pushed, so this
won't affect the Mac clone). Worth adding to `.gitignore` if they're
routine Hailo/Pi runtime artifacts rather than something meaningful —
flagging here so whoever's on the Pi next doesn't have to rediscover them.
