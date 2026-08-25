# Meeting and Work Session Log

---

## August 25, 2026 — Work Session (Pi: camera-identity diagnostic, road-test systemd deployment, OLED resilience, buzzer shutdown race)

**Present:** Deepansh (Pi bench, Claude Code running directly on the Pi)
**Focus:** Work through the open items from the Aug 22 session (camera
identity, mAP-drop measurement, OLED permanent fix, road-test readiness) —
everything doable from the Pi without dataset access or physical soldering.

### Camera identity / magenta cast — new evidence, still not 100% closed

Wrote `scripts/diagnose_camera_ir.py`. Two software-side checks:

- **Tuning file selection.** The Pi's imaging stack ships two IPA tuning
  files for this sensor (`/usr/share/libcamera/ipa/rpi/pisp/imx219.json`
  and `imx219_noir.json`), and libcamera auto-selects one based on the
  connected module's identity. It picked `imx219.json` (the has-IR-filter
  tuning), not the NoIR one.
- **Raw sensor channel response.** Captured with white balance forced to
  unity gains (`--awbgains 1.0,1.0`, i.e. before any auto-correction):
  R=74.1, G=115.0, B=32.7 (R/G=0.64, B/G=0.29) — green-dominant, which is
  what an IR-cut-filtered sensor should show (near-IR bleed into R/B is
  blocked). A true NoIR module would show elevated R and/or B relative to
  G, the opposite pattern.

Both signals now point the same way: **standard imx219, not NoIR.** This
is software-side evidence, not a physical guarantee, and doesn't explain
the magenta cast seen once under indoor lighting on Aug 2 — that could
still be an unrelated white-balance/lighting artifact rather than a
missing IR-cut filter. The genuinely definitive test (IR remote + button
press, invisible flash visible on a NoIR sensor) still hasn't been done —
needs an IR remote in hand, not something resolvable from here. Documented
in the script's own docstring so it's not lost again.

### mAP drop measurement (float32 vs INT8) — scaffolded, not run

This is Phase 3's last exit criterion (flagged as "not done" in the Aug 12
entry below) but genuinely can't be executed from the Pi: it needs the
held-out test split (SSD only, per CLAUDE.md section 7 — the raw dataset
never goes on the Pi) and `hailo_sdk_client` (Colab's `hailo_env` only —
the Pi has the lighter `hailo_platform` runtime for running an
already-compiled `.hef`, not the Dataflow Compiler).

Split the work into a part that *could* be built and verified here, and a
part that has to wait for the next Colab session:

- `scripts/map_eval/metrics.py` — a small, framework-agnostic COCO-style
  mAP implementation (IoU matching, 101-point interpolated AP, mAP50 and
  mAP50-95) with no dependency on the dataset or Hailo SDK. Unit-tested
  now: `tests/test_map_metrics.py`, 9 cases (perfect detections → AP 1.0,
  no detections/no ground truth → AP 0.0 not a crash, a deliberately
  offset box that clears IoU 0.5 but fails the tighter mAP50-95
  thresholds — confirms the two metrics actually diverge as expected).
  All passing (47/47 across the full suite, up from 38).
- `scripts/eval_map_int8_colab.py` — driver script for the *next* Colab
  session: loads the already-quantized `.har` from Aug 12, runs
  `ClientRunner.infer()` in both `SDK_NATIVE` (float32) and
  `SDK_QUANTIZED` (INT8) contexts against the test split, feeds both
  through `metrics.compute_map()`, prints the drop. **Not run
  end-to-end** — written blind, without dataset or `hailo_sdk_client`
  access here, so its docstring says explicitly to sanity-check the
  float32 number against the known ultralytics figures (mAP50 0.823,
  mAP50-95 0.638, CLAUDE.md section 8) before trusting the INT8 side; if
  those don't roughly match, the eval harness itself (box convention,
  label parsing, class mapping) is wrong, not the model.

### Road-test deployment — systemd service, verified working

Wrote `scripts/wildlife-detection.service` +
`scripts/run_wildlife_detection_road.sh` +
`docs/road-test-deployment.md`, so a road test doesn't depend on an SSH
session staying attached: auto-restart on crash, clean LED/buzzer/OLED
shutdown on stop (reuses the signal-handling fix from Aug 22), full 8-LED
bar + raised buzzer volume (0.6) by default, tunable via
`systemctl edit` environment overrides.

Installing the unit needs `sudo`, which needs an interactive password —
couldn't do that step here. **Still needs Deepansh to run, once:**

```
sudo cp scripts/wildlife-detection.service /etc/systemd/system/
sudo systemctl daemon-reload
```

(full details in `docs/road-test-deployment.md`). Verified the launcher
script itself directly (not yet through the installed unit): started
clean, `SIGTERM` produced a clean shutdown log, process fully gone
afterward.

**Also added:** `run_wildlife_detection.py` now auto-loads the real
calibrated focal length from `config/camera_matrix.npy` (the Aug 22
calibration) if `--focal-length-px` isn't passed explicitly, instead of
silently needing it re-typed on every run. Confirmed live: "Using
calibrated focal length from config/camera_matrix.npy: 2547.08px".

### Bug found and fixed: buzzer shutdown race

While verifying the road-test launcher's `SIGTERM` path, hit a real crash:
`AttributeError: 'NoneType' object has no attribute 'ChangeDutyCycle'` in
a background alert thread. Root cause: `_shutdown_alerts()` calls
`buzzer.cleanup()`, which nulls `self._pwm`/`self._gpio` — but if a
`continuous_rapid()` pattern (fired on its own daemon thread by
`AlertController.trigger()`) is still mid-loop calling `_set()` at that
exact moment, it dereferences the now-None PWM object. A shutdown landing
mid-alert is a completely realistic scenario in the car (kill the process
while an animal warning is actively firing).

Fixed in `src/alerts/buzzer.py`: added a `threading.Lock`, and `_set()`/
`cleanup()` both take it and no-op instead of crashing if the pin is
already torn down (safe either way — a no-op means the pin is already
safely deinitialized). Verified two ways: (1) re-ran the same
launch-then-SIGTERM test that first surfaced it — clean shutdown, no
traceback; (2) wrote a deterministic 20-trial stress test with a fake
GPIO backend that reliably reproduced the race pre-fix and confirmed zero
crashes post-fix.

Also made the OLED driver (`src/alerts/oled_display.py`) resilient to its
own known issue (I2C connector drop under vibration, Aug 12 and Aug 22
entries) rather than just documenting it: every I2C call now retries with
a short backoff and reconnect attempt, degrading to a skipped update
(logged, not crashed) if the bus stays unreachable — LED and buzzer stay
the primary alert either way, so a flaky OLED can no longer take down the
whole pipeline mid-drive. This is a software mitigation, not the physical
fix (reseat/recrimp/resolder) the connector still needs — that's still
Deepansh/Aditya's hands, not something fixable from here.

### Not done / open

- **IR-remote test** for the camera — the one physical check that would
  actually settle the identity question; needs an IR remote in hand.
- **mAP drop measurement** — script written, not run; needs the next
  Colab session with the SSD dataset mounted.
- **systemd unit not yet installed** — needs Deepansh to run the two
  `sudo` commands above, once.
- **OLED connector's permanent physical fix** (resolder/recrimp) — still
  outstanding; today's work only made the software degrade gracefully
  around it, doesn't fix the underlying intermittent connection.
- **No real road test yet** — everything through today has been bench/
  backyard testing.

---

## August 22, 2026 — Work Session (Pi: first real calibration, live pipeline, three shutdown/detection bugs found and fixed)

**Present:** Deepansh (Pi bench, Claude Code running directly on the Pi)
**Focus:** First real checkerboard calibration (fx no longer a placeholder),
first `--live-alerts` runs against the newly-calibrated pipeline, and three
real bugs surfaced and fixed along the way.

### Calibration

- First attempt aimed the camera at the sky by mistake (checkerboard just a
  sliver at the frame edge) — 0 usable photos. Re-aimed, but the board was
  shot directly into the sun, which put heavy lens flare across it; only
  7/20 photos passed corner detection and reprojection error was 2.0px.
- Repositioned so the sun was behind the camera instead of behind the board.
  Detection rate improved but reprojection error got *worse* (4.0px) —
  turned out the printed checkerboard itself was warped/creased (visible
  ripple in the top edge line, glossy specular streaks), violating the flat-
  plane assumption calibration math depends on. Re-mounted the printout on a
  rigid flat backing; error dropped to 1.21px on 8 photos immediately.
- Chased more samples for a better-conditioned fit (30 photos at 1s
  intervals, then +15 more at 1.5s): count went up but so did error (1.88px,
  1.91px on 45 photos) — faster pacing introduced motion blur that outweighed
  the benefit of more samples. Lesson: for this setup, slower/steadier beats
  faster/more.
- Final approach: ran `cv2.calibrateCamera` once across all 20 accepted
  photos from the 45-photo pool, ranked each by its own per-image
  reprojection error, kept the best 16, and recalibrated on just those.
  **Final result: 16 photos, reprojection error 1.34px, fx=2544.77px,
  fy=2549.39px.** `config/camera_matrix.npy` / `config/dist_coeffs.npy`
  committed.
- Still open: the magenta/pink color cast noted back on Aug 2
  (`docs/open-issues-2026-08-02.md`) showed up strongly again in every
  calibration photo today, including frames with no direct backlighting —
  more evidence toward "this sensor behaves like a NoIR variant regardless
  of what the EXIF model string says," still not physically confirmed.

### Live pipeline runs

- `models/bc_dashcam_yolov8n.hef` checksum reverified against the value
  recorded in `CLAUDE.md` for the Aug 12 max-optimization compile — matches.
- First `--live-alerts` run crashed at startup: `OledDisplay.__init__`
  raised `OSError: [Errno 121] Remote I/O error` even though `i2cdetect`
  showed the display present at `0x3c` — the same known loose-connector
  issue as Aug 12, this time failing on the *write* burst rather than the
  bus scan. Reseating the connector fixed it and it held up cleanly through
  every subsequent run today, including one sustained ~3.5-minute run under
  heavy alert load.
- Ran against an iPad displaying a coyote image for an extended period:
  "coyote" was correctly the dominant class (652/1559 detections in the
  first run), confirming the model responds to the intended species. Other
  species mixed in throughout (moose, deer, cougar, raccoon, elk) — matches
  the already-documented iPad glare/moiré accuracy issue from Aug 12
  (`docs/meeting_log.md`, Aug 12 entry), reproduced again today.
- Pointed at an ordinary indoor desk (no iPad, no wildlife — just a mouse,
  fingers, keyboard) with `--live-alerts` running: the pipeline fired
  constant low-confidence detections across every species class. Root cause
  and fix below (Bug 3).

### Bugs found and fixed

1. **LED/buzzer did not turn off when the process was killed.** `kill <pid>`
   sends SIGTERM, which Python has no default handler for (unlike SIGINT/
   Ctrl+C) — the process died immediately, skipping all cleanup, and left
   the WS2812B LEDs latched at their last color (they hold state until
   explicitly cleared) and the buzzer's software-PWM pin possibly stuck
   HIGH. Had to force the buzzer pin off manually mid-session as an
   immediate fix. Root-caused and fixed properly: `hailo_apps` installs its
   *own* SIGINT handler (`GStreamerDetectionApp.__init__`) that tears the
   process down without ever returning control to a plain `try/finally`, so
   a simple finally block doesn't work either. Fix
   (`scripts/run_wildlife_detection.py`): a `_shutdown_alerts()` handler now
   chains in *front of* both SIGINT and SIGTERM, so LED/buzzer/OLED get
   forced off synchronously as the very first thing on either signal,
   independent of whatever hailo_apps or Python does afterward. Verified
   with `kill` (plain SIGTERM) — cleanup now prints and fires correctly.
2. **Process lingered after shutdown.** Even after the fix above, the OS
   process stayed alive for a while after cleanup ran and printed complete —
   non-daemon camera/GStreamer worker threads kept it up, which would have
   blocked the next run from acquiring the camera/Hailo device. Fixed with a
   3-second hard-exit safety net (`os._exit`, via a daemon timer thread)
   that starts right after hardware cleanup. Verified: process is now fully
   gone well within the window on both SIGINT and SIGTERM.
3. **Pipeline fired on almost anything indoors** (mouse, fingers, keyboard —
   no wildlife in frame). Root cause: `hailo_apps`' own NMS score threshold
   is hardcoded at 0.3 inside the vendored library (`detection_pipeline.py`),
   not exposed as a CLI flag, and our callback applied no threshold of its
   own on top of it. Fixed by adding a second, stricter gate in the
   project's own callback (`--min-confidence`, default 0.6,
   `DEFAULT_MIN_CONFIDENCE` in `run_wildlife_detection.py`) applied after
   the Hailo pipeline's NMS has already run.
- Also made `Buzzer.cleanup()` idempotent (`src/alerts/buzzer.py`) since the
  new shutdown path can call it more than once (once from a signal handler,
  once again from the `finally` safety net).

### Not done / open

- float32-vs-INT8 mAP drop measurement (Phase 3 exit criterion) — still the
  single most important number missing to properly interpret species-
  accuracy results.
- Camera identity / magenta color cast (NoIR vs standard) — still
  unresolved, more evidence gathered today, no physical resolution yet.
- No real road test yet — everything today was bench/backyard, against an
  iPad and an indoor desk, not real wildlife or road-perspective footage.
- OLED connector still needs a permanent physical fix (reseat/resolder) —
  today's reseat held, but that's been true before (Aug 12) and it
  eventually dropped again under load that same session.

---

## August 12, 2026 — Work Session (Pi: live test of the max-optimization `.hef`)

**Present:** Deepansh + Aditya (Pi bench)
**Focus:** First live-camera test of the Aug 12 max-optimization `.hef`
against real animal photos, plus continued hardware bring-up (camera,
OLED, LED bar, buzzer volume)

### What was done

- **Camera reconnected after physical rework.** Two distinct failure modes
  hit back-to-back: (1) CSI not detected at all after reconnecting (`No
  cameras available!`, no probe activity in `dmesg`) — expected, since CSI
  isn't hot-pluggable and just needed a reboot; (2) after that reboot, the
  driver *did* probe the sensor but failed with `imx219 11-0010: error
  -EREMOTEIO: failed to read chip id 219` — a genuine bad connection (cable
  not fully seated / latch not closed), fixed by physically reseating the
  ribbon cable. Camera has been stable since.
- **Buzzer volume fixed and OLED layout improved** (`src/alerts/buzzer.py`,
  `src/alerts/oled_display.py`) — PWM-driven duty-cycle volume control
  instead of full-blast digital on/off, and a centered/auto-fit-font OLED
  layout. Also found and fixed a real bug: installing `adafruit-blinka`
  into the `hailo-rpi5-examples` venv (needed for `board`/`busio`/
  `neopixel` imports) pulls in a real `RPi.GPIO` as a transitive
  dependency, silently shadowing the `rpi-lgpio` shim Pi 5 needs —
  reproduced as `RuntimeError: Cannot determine SOC peripheral base
  address`; fixed by uninstalling the stray `RPi.GPIO` from that venv.
- **`pipewire`/`wireplumber` (desktop session services) intermittently grab
  the camera device** (`/dev/video4`), causing `Failed to queue buffer:
  Operation already in progress`. Not our code — stopping those services
  (`systemctl --user stop wireplumber pipewire ...`) frees the device.
  They restart on login/reboot, so this needs redoing each session until a
  more permanent fix (e.g. a udev rule or disabling the services) is put
  in place.
- **Live species test against the new max-optimization `.hef`**, ~10 rounds
  of holding animal photos on an iPad up to the camera with `--live-alerts`
  running (real LED bar, OLED, buzzer, not simulated). **Accuracy was still
  not reliable** — across rounds the dominant reported species varied
  unpredictably (raccoon, moose, cougar, coyote, and deer each topped
  different rounds) with no consistent single wrong answer, which argues
  against a remaining indexing bug (already verified separately against
  the real compile config) and points instead at the already-documented
  domain-shift limitation (CLAUDE.md section 14) — an iPad screen
  introduces glare, moiré (pixel-grid-on-pixel-grid interference), and
  backlit color shift that real camera-trap training photos don't have.
  **The float32-vs-INT8 mAP drop still hasn't been measured**, so it's
  also possible this specific `.hef`'s real-world accuracy ceiling is part
  of the story, independent of the screen artifact issue. Printed matte
  photos or the actual road test would both give a cleaner read than an
  iPad screen.
- **OLED intermittently lost I2C communication mid-run**, several times
  across the ~10 rounds: `OSError: [Errno 121] Remote I/O error` from the
  `adafruit_ssd1306` write path. Sometimes this happened inside a running
  alert (killing just that background thread, detections kept logging
  fine); twice it happened at `OledDisplay.__init__` and crashed the whole
  script before the camera pipeline even started. `i2cdetect -y 1` showed
  the display at `0x3c` again within seconds each time — this is a
  physical connection issue (loose SDA/SCL/ground under handling), not a
  code or address/config problem. Worth securing that connector (or
  resoldering) before relying on the OLED for anything unattended.
- LED bar (8-pixel) and buzzer (post volume-fix) had no issues across all
  ~10 rounds — only the OLED connection was flaky.

### Not done / open

- float32-vs-INT8 mAP drop measurement (Phase 3 exit criterion) — still
  the single most important number missing to properly interpret today's
  species-accuracy results.
- Camera calibration (Aditya) — `scripts/run_wildlife_detection.py` is
  still running on a placeholder focal length, so all distance/zone
  numbers from today's test are not meaningful.
- Camera identity (NoIR vs standard) — still unresolved from the earlier
  Aug 2 session.
- OLED connector needs a physical fix (reseat/resolder) before it can be
  trusted for unattended operation.

---

## August 12, 2026 — Work Session

**Present:** Deepansh (Mac + Colab)
**Focus:** Re-running quantization with a full-size calibration set and
completing the max-optimization compile that was deferred twice in the
July 29-30 session

### Why this session happened

The July 30 `.hef` (committed to the repo) was compiled from a
401-image calibration set at optimization level 0/1 — Hailo's Dataflow
Compiler had explicitly warned that AdaRound and Quantization-Aware
Fine-Tuning were skipped because the calibration set was under its
1,024-image recommendation. Two earlier attempts to run
`compiler_optimization_level=max` for the best possible partition had
both been interrupted before finishing (once by what looked like an
accidental cell interrupt, once by a Colab VM reset during an unattended
gym trip) — see the July 29-30 entry below.

### What was done

**Expanded the calibration set to all 2,001 training images** (up from
401), sampled from the SSD's `yolo_dataset/train/images` — same rule as
before, training split only, held-out test split untouched. Verified
before checking Hailo's own docs that the "1,024" threshold in the
optimizer's warning isn't arbitrary: Hailo's `post_quantization_optimization`
algorithms (`finetune`, `adaround`) each default to a `dataset_size` of
1,024/256 respectively — so the fix was genuinely just providing enough
data, not a special flag.

Uploaded the 1.1 GB calibration zip through Drive (not Colab's direct
upload widget, which corrupted a 524 MB file in the July 29-30 session).
Rebuilt `hailo_env` on a fresh GPU + High-RAM runtime, re-verified the DFC
wheel's byte count before installing, and reused the already-parsed
`bc_dashcam_yolov8n_manual.har` from July 30 (no need to re-parse, since
the manual end-node fix from that session was still valid).

**Re-ran `hailo optimize`** with the larger calibration set. Result:
optimization level 2 selected automatically (no "reducing level" warning
this time), and — critically — **Quantization-Aware Fine-Tuning actually
ran** (4 real epochs, 128 steps each, ~8m14s, drawing 1,024 entries from
the calibration pool), superseding the July 30 run's Bias-Correction-only
result. Bias Correction and AdaRound both showed as "skipped" at this
level — not a regression, since full fine-tuning is a strictly more
thorough technique that supersedes the two lighter approximation methods.

**Re-ran `hailo compiler`** with `compiler_optimization_level=max` against
this better-optimized HAR. This time it ran to completion: 133 partition
iterations across ~5 hours of wall-clock time (mostly unattended), settling
on a 3-context partition, each context individually allocated with zero
reverts, followed by a 17-second final HEF build.
**`"Successful Compilation"`** — the max-optimization result this project
has been chasing since July 29.

One practical thing worth recording: partway through the run, the browser
tab's live connection to Colab dropped (the UI showed "Reconnect"), but
**the underlying compute kept running server-side and finished
successfully anyway**. This is a useful data point distinguishing two
different failure modes seen across these sessions: a *browser-side*
disconnect (recoverable, as happened here) versus an actual *Colab
VM/session reset* (not recoverable, as happened twice on July 29-30) — the
two look similar from the UI but have very different consequences.

**Replaced the committed `.hef`.** The new compile produced the same
filename (`bc_dashcam_yolov8n.hef`), overwriting the file on Drive. This
meant the copy already committed to the repo from July 30 was now stale.
Downloaded the new file, verified its checksum differed from the old one
(confirming it was genuinely the new compile, not a stale re-download),
and committed the replacement: SHA-256
`8886546c919420f652090e78275785b2e3e034e45c8597ea9734d75a66fff10f`,
12,196,315 bytes (up from the July 30 version's 9,497,066 bytes — larger
file is consistent with the more thorough optimization changing per-layer
bit-width allocations).

### Not done

- **mAP degradation measurement (float32 vs INT8)** is now the sole
  remaining Phase 3 exit criterion — this is the natural next step, now
  that a properly-optimized `.hef` exists to measure.
- **The Pi has not yet pulled this new `.hef`.** Next action: `git pull`
  on the Pi, verify the checksum above, and re-run
  `scripts/run_wildlife_detection.py` to confirm the pipeline still runs
  cleanly against the new (larger, differently-quantized) file.

---

## August 2, 2026 — Work Session

**Present:** Deepansh (Mac, resolving issues flagged by a same-day Pi session)
**Focus:** Fixing `docs/open-issues-2026-08-02.md`, left by Claude Code on
the Pi after wiring the compiled `.hef` into the live detection pipeline

### Context

Earlier today, the Pi session reconnected the camera, wrote
`scripts/run_wildlife_detection.py` (replacing `hailo_apps`' stock COCO
callback with this project's real approach-vector → risk-selection →
distance → zone → alert pipeline), and ran it end-to-end successfully
against both the stock sample video and a live indoor test. It left three
issues for the Mac side, ranked by actionability.

### Resolved

**Label index convention (was flagged BLOCKING).** The Pi's
`config/hailo_labels.json` had guessed Hailo's usual `0=unlabeled,
1-7=species` convention, copied from the only reference file available
locally (`hailo-rpi5-examples/local_resources/barcode-labels.json` — a
different model's config, not applicable here). The actual compile
config was built in the Jul 29-30 Colab session and never got committed —
reconstructed it exactly from that session's transcript and committed it:
`models/nms_config_7class.json` (the custom NMS postprocess config,
`"classes": 7`, no unlabeled/background offset) and
`models/bc_dashcam_yolov8n.alls` (the model script — normalization +
sigmoid activations + the NMS postprocess call). Neither file has an
unlabeled/background class, mirroring Hailo's own official reference
config for COCO (class 0 = "person", not background). Combined with
`scripts/build-yolo-dataset.py`'s alphabetical 0-indexed class list,
this confirms: network output index 0-6 maps **directly** to
bear/cougar/coyote/deer/elk/moose/raccoon, no offset. Fixed
`config/hailo_labels.json` (removed the `"unlabeled"` entry) and updated
`scripts/run_wildlife_detection.py`'s docstring accordingly. **Needs a
`git pull` on the Pi before the next real-animal test** — the Pi's copy
is still running the wrong label list until then.

**Stray runtime files (low priority).** Added `hailort.log`,
`reboot.save`, `reboot.save.*` to `.gitignore` — routine Hailo/Pi runtime
artifacts, not meaningful to track.

**Camera calibration prep.** Can't run the actual checkerboard
calibration without the physical session (Aditya, per
`docs/interface_contract.md` section 2), but wrote
`scripts/calibrate_camera.py` now so it's ready the moment calibration
photos exist: takes a folder of checkerboard photos, runs
`cv2.findChessboardCorners` + `cv2.calibrateCamera`, saves
`camera_matrix.npy`/`dist_coeffs.npy`, and prints the focal length in
pixels to feed directly into `run_wildlife_detection.py --focal-length-px`.

### Not resolved — genuinely needs the Pi / physical hardware

**Camera identity is contradictory, not settled.** The `imx219` EXIF
model tag (used earlier to conclude "not the NoIR variant") can't
actually distinguish NoIR from standard — same sensor chip, different
lens filter, EXIF doesn't see the filter. A live preview shot today under
indoor fluorescent lighting showed a strong magenta/pink color cast,
which is the classic symptom of *no* IR-cut filter — i.e. evidence now
points toward it *being* NoIR after all. The two pieces of evidence
conflict and neither is conclusive. Resolution needs either a physical
check (the module usually has "NoIR" printed on it) or a controlled test
(point an IR remote at the camera while pressing a button — a NoIR
sensor shows the LED as a bright dot on screen, a standard sensor shows
nothing). Flagged in CLAUDE.md's hardware table so this doesn't get
silently treated as settled either way. This matters for the nighttime
range discussion (`docs/development_phases.md` Phase 5) — don't assume
IR sensitivity either direction until this is checked.

### Still open (unchanged from before today)

Max-optimization compile and the float32-vs-INT8 mAP measurement are
still deferred (see Jul 29-30 entry below) — today's fixes only affect
correctness (are labels right), not quantization quality.

---

## July 29-30, 2026 — Work Session

**Present:** Deepansh (solo, Colab + Claude Code on Mac)
**Focus:** Phase 3 — INT8 quantization of `best.pt` and first successful Hailo-8L compilation

### Completed

**Compute setup.** Purchased Colab Pro (CA$13.99/mo). Confirmed a High-RAM
runtime (50 GB, comfortably above the ~32 GB Hailo Dataflow Compiler
requirement). Later added a T4 GPU to the same runtime — turned out to be
necessary, not optional (see below).

**Environment.** Hailo's Developer Zone only offers the Dataflow Compiler
(DFC) for Python 3.10, not Colab's default 3.12. Built an isolated `hailo_env`
via Miniconda inside the Colab session for this exact reason. Installed
`hailo-dataflow-compiler==3.34.0` (524 MB wheel — first upload attempt to
Colab silently truncated to ~174 MB and produced a corrupted zip archive;
fixed by routing the transfer through Drive instead of the direct browser
upload widget, and verifying exact byte counts before trusting any transfer
again). Installing `ultralytics` afterward bumped `numpy` to 2.2.6, breaking
the DFC's `numpy==1.26.4` pin — fixed by reinstalling the pinned version
after `ultralytics`.

**Export.** `best.pt` → ONNX (opset 11, `imgsz=640`) via `ultralytics`.
Output shape `(1, 11, 8400)` confirmed correct: 4 bbox coords + 7 class
scores, matching the 7-species head exactly.

**Calibration set.** Built a 401-image calibration set, proportionally
sampled across all 7 classes from the training split only (not the held-out
test split, to avoid contaminating the later mAP-drop measurement) — pulled
directly from the T7 SSD. Below Hailo's recommended 1,024 for best accuracy;
noted as a follow-up.

**The real blocker — Hailo's automatic postprocess extraction doesn't
compile for this model.** `hailo parser onnx` auto-recommended end nodes at
`/model.22/Sigmoid` and `/model.22/dfl/Reshape`, and the resulting HAR bundled
its own auto-generated `.postprocess.onnx` (visible as two output layers,
`activation1` and `depth_to_space1`). This parsed and optimized fine (first
attempt was forced to optimization level 0 — no GPU present, and calibration
set below 1,024 — a real quality problem in its own right), but **compilation
failed twice** with `BackendAllocatorException: ... Agent infeasible` /
`No valid partition found`, naming `concat14` and a `depth_to_space1` defuse
layer as the immediate cause. Adding a GPU (fixing the optimization level
1 → real Bias Correction ran) did **not** fix the compile failure — proving
the problem was structural (the auto-generated postprocessing subgraph
itself), not a quantization-quality issue.

**Fix: bypass the automatic extraction, use Hailo's own official manual
pattern instead.** Hailo's public Model Zoo reference (`yolov8n.alls` +
`yolov8n_nms_config.json`, both fetched from
github.com/hailo-ai/hailo_model_zoo) doesn't use auto-extraction at all — it
stops parsing at the six raw conv outputs (3 box-regression, 3 class-score,
one pair per stride 8/16/32) and does NMS/DFL-decode entirely via an explicit
CPU-side `nms_postprocess` JSON config. Re-parsed `best.onnx` with explicit
`--end-node-names` at those six conv layers. `hailo har info --verbose`
confirmed the internal layer names Hailo assigned —
**`conv41/42`, `conv52/53`, `conv62/63`** — the *exact same numbers* as
Hailo's own official reference config, strong confirmation the architecture
translated correctly. Built a custom `nms_postprocess` JSON (`"classes": 7`
instead of the reference's 80, same `bbox_decoders` structure with the
correct layer names) and a model script (normalization +
`change_output_activation` sigmoid on the 3 class layers + the NMS config).

**Result: first successful compile.** Re-ran optimize (level 1, GPU present)
and compile with this manual config — **compiled cleanly in 14 seconds**,
where the auto-extraction version had failed twice. Output:
`bc_dashcam_yolov8n.hef` and `bc_dashcam_yolov8n_compiled.har`, saved to
Drive (`bc-dashcam/run1_7class/weights/`).

**Quantization quality recorded so far:** SNR (signal-to-noise ratio,
higher is better) from the level-1 optimize run — `output_layer2: 15.95 dB`,
`output_layer1: 17.79 dB`. Moderate, not exceptional; consistent with
optimization level 1 (Bias Correction only) rather than max (AdaRound +
QAT fine-tuning), and a 401-image calibration set below the 1,024
recommended. Expected to improve in a later pass.

### Not done / deferred

- **Max-optimization compile not completed.** Attempted
  `performance_param(compiler_optimization_level=max)` for the
  best possible partition (found several improving valid partitions,
  34.1% → down to marginal %, before being interrupted). Colab sessions
  disconnected/reset twice during unattended waits (once mid-search, once
  right after promising to leave it running during a gym trip) — unattended
  multi-hour Colab jobs on this setup are not reliable enough to trust yet.
  **Deferred to a dedicated, uninterrupted session** — likely best attempted
  overnight rather than while stepping away mid-day. The working `.hef` in
  hand right now is from the plain (non-max) compile.
- **Calibration set is 401 images, not the recommended 1,024+.** Worth
  expanding before the max-optimization pass, since both factors (GPU +
  calibration size) independently affect the optimization level Hailo will
  allow.
- **mAP-drop measurement (float32 vs INT8) not yet done** — this is an
  explicit Phase 3 exit criterion, deferred until the max-optimization
  `.hef` is ready (measuring against the level-1 version now would be
  measuring a known-suboptimal intermediate, not the final model).
- **`.hef` not yet on the Pi.** Next concrete step: transfer
  `bc_dashcam_yolov8n.hef` to the Pi and wire it into the
  `hailo-rpi5-examples` detection pipeline in place of the stock demo
  model, with the live camera feed, to get the first real end-to-end
  detection test.

### Key lesson for future quantization work on this or similar models

If a custom YOLOv8-family model on Hailo-8L fails to compile with
`Agent infeasible` / `No valid partition found`, and the HAR contains an
auto-generated `.postprocess.onnx` with `depth_to_space`/reshape output
layers — don't keep tuning quantization or compiler flags. Re-parse with
explicit `--end-node-names` at the raw per-stride conv outputs instead, and
build a manual `nms_postprocess` JSON (adapt Hailo's own official
`yolov8n.alls` reference, just change `"classes"` and confirm layer names
via `hailo har info --verbose`). This is what actually fixed it.

---

## July 5, 2026 — Work Session

**Present:** Deepansh (solo, with Claude Code on the Pi)
**Focus:** Phase 2 hardware bench milestone + software groundwork while camera/GPS are in transit

### Completed
- Pi 5 + Hailo-8L bench verified end-to-end: `hailortcli scan`/`fw-control identify`
  confirm the NPU at `0001:01:00.0`; ran the stock `hailo-rpi5-examples`
  detection demo (YOLOv8s) on the bundled sample video with a live display
  window, bounding boxes, and tracking IDs.
- Found and fixed a real bug along the way: `hailo-apps-infra`'s bundled C++
  postprocess source doesn't compile against the installed tappas-core 5.1.0
  (`HailoTensor::vstream_info()` was removed), which segfaulted every basic
  pipeline. Fixed by symlinking tappas-core's own prebuilt equivalent
  (`libyolo_hailortpp_post.so`) into the path the pipeline expects. Confirmed
  via `hailortcli monitor` that the Hailo-8L NPU (not the CPU) is doing the
  inference: device utilization 43-50%, ~30fps sustained, 0% frame drops.
- Enabled I2C on the Pi (`raspi-config nonint do_i2c 0`) ahead of wiring the
  SSD1306 OLED — takes effect after a reboot, not yet rebooted.
- Since the camera (with Aditya) and GPS module (still being ordered) are the
  only two blockers, used today to build everything in `src/` that doesn't
  need either: config loaders, thin-lens + TTC distance estimation with
  conservative fusion, three-tier zone classification, the approach-vector
  filter, highest-risk-only alert selection, a GPRMC NMEA parser (built and
  tested purely from the example sentence in `gps_interface_spec.md` — no
  physical GPS needed for the parsing logic itself), the JSONL detection
  logger, and driver code for the LED bar / OLED / buzzer (all three are
  in-hand hardware, just not yet wired to the Pi — I2C was still disabled
  and no devices were detected on the bus at the start of today).
- All of the above lives behind a `simulate=True` flag on the hardware
  drivers so the zone-to-output logic is fully unit tested (38 tests
  passing) without any hardware attached; the same code path runs for real
  once things are wired. Added `scripts/test_led_bar.py`,
  `scripts/test_oled.py`, `scripts/test_buzzer.py` as the physical smoke
  tests for whenever the wiring happens (matches the Phase 2 kickoff
  verification steps: amber pulse 0.3s / red flash 0.1s, OLED text render,
  two-short / continuous-rapid buzzer patterns).
- Added `requirements-pi.txt` (RPi.GPIO, neopixel/blinka incl. the Pi5-specific
  neopixel driver, ssd1306, pyserial, pytest) and a `venv` at the repo root
  for Pi-side deployment code, separate from the training-machine
  `requirements.txt`.

### Not done / still blocked
- LED bar / OLED / buzzer are not physically wired yet, so
  `scripts/test_*.py` haven't been run for real — that's the next hands-on
  step once there's time to breadboard them (doesn't need Aditya or new
  parts, just bench time).
- Camera and GPS integration untouched, as expected — waiting on parts
  (camera arriving ~Jul 8 with Aditya; GPS still being ordered).
- Buzzer GPIO pin in `src/alerts/buzzer.py` is a placeholder (17) — not yet
  confirmed against actual wiring since nothing's been wired.

### Next
- Wire up LED bar / OLED / buzzer on the bench and run the three hardware
  smoke test scripts; reboot to activate I2C first.
- Once camera arrives: `rpicam-hello`, then live feed through the Hailo demo
  pipeline (Phase 2 kickoff steps 9-10).
- Start the INT8 quantization path for `best.pt` (Phase 3) — needs a
  32GB-RAM Colab session, not blocked by any missing hardware.

---

## May 15, 2026 — Work Session

**Present:** Deepansh (solo)
**Focus:** Initial project setup

### Completed
- GitHub organization and private repo created
- Branch protection enabled on main
- Initial project structure established
- Began dataset survey research across Caltech Camera Traps and iNaturalist

---

## May 16, 2026 — Work Session

**Present:** Deepansh (solo)

### Completed
- Dataset survey finished for all 7 target species across Caltech Camera Traps and iNaturalist
- Species counts and pull strategy documented in `dataset_survey.md`
- iNaturalist API tested and confirmed working (2,313 moose BC observations accessible)
- MegaDetector v5a installed and validated on 50 moose test images
- Detection rate on raw iNaturalist images: 57% usable (29/51 above 0.5 confidence)
- GPU runtime confirmed on Colab (Tesla T4)
- Google Drive mounted for persistent storage
- Directory structure created at `MyDrive/bc-dashcam/`
- Full download pipeline ready for all species

### Decisions
- Cougar: global iNaturalist pull approved due to insufficient BC-only coverage (332 images)
- Per-species download cap set at 500 images for initial pull
- MegaDetector confidence threshold set at 0.5 for usable annotation cutoff

### Blockers
- None on Deepansh's side

### Next
- Run full download pipeline for all 7 species
- Start MegaDetector batch annotation on downloaded images

---

## May 20, 2026 — Supervisor Meeting

**Present:** Deepansh, Aditya, Dr. Thomas Johnson
**Location:** Dr. Johnson's office, UBC Okanagan

### Presented
- Pipeline decision tree diagram (drawn on iPad)
- Data flow diagram (drawn on iPad)
- Dataset survey results and pull strategy
- MegaDetector filtering approach

### Dr. Johnson Feedback
1. Confidence scores must account for lighting conditions — nighttime and low-visibility detections should not be treated the same as daytime
2. Recommended a two-stage pipeline: animal presence detection first (MegaDetector-style), then species classification (YOLOv8n)
3. Pipeline must be documented as both a decision tree and a data flow diagram — completed and presented in this meeting
4. Approach vector: only trigger alerts on animals approaching the vehicle, not retreating. A shrinking bounding box indicates the animal is moving away.
5. Multiple detections in a single frame: alert on the highest-risk class only. Log all detections.
6. Audio is the primary warning modality — drivers do not look at dashboards
7. Algorithm validation required: held-out test set, mAP, per-class FP/FN rates, and a road test
8. GPS encounter dataset has a downstream connection to ICBC wildlife-collision insurance data — this is the research contribution angle

### Action Items
- Implement approach vector check in proximity zone logic
- Implement highest-risk-class alert selection for multi-detection frames
- Define held-out test set before any training begins
- Prepare next update with concrete training results

---

## May 26, 2026 — Supervisor Meeting

**Cancelled.**

---

## June 3, 2026 — Status Report Submitted

**Submitted to:** Dr. Johnson (written status report)

Summary: Dataset pipeline complete (2,860 usable images across 7 species). Initial YOLOv8n training run completed (mAP50: 0.823, mAP50-95: 0.638). Hardware ordered and arriving. Roboflow dependency removed; full pipeline runs locally.

---

## June 16, 2026 — Supervisor Meeting

**Present:** Deepansh, Aditya, Dr. Johnson

### Reported
- Limited progress due to exam period (April-June)
- Dataset status: all 7 species downloaded, filtered, uploaded to Roboflow
- Hardware: Pi 5 and Hailo AI Kit in hand, camera with Aditya
- Roboflow upload progress and the class-label "?" issue

### Discussion
- Dr. Johnson asked about GPU/RAM access needs
- Prepared justification: Hailo Dataflow Compiler requires 32 GB RAM for INT8 compilation (cite Hailo's own toolchain docs), Colab free tier disconnects mid-training, augmentation pipelines slow on laptop

### Next Meeting
- Not yet scheduled. Will confirm with Dr. Johnson.

---

## June 25, 2026 — Session Start

**Present:** Deepansh (solo)

### Status
- Resuming after exam period
- Phase 1 (Data + Documentation) mostly complete, Roboflow class-label bug still blocking
- Phase 2 (Hardware Bench Setup) begins June 26
- Full project handoff document written to establish context for this session
- All documentation updated to reflect current hardware (Pi 5 + Hailo-8L, replacing earlier Pi 4 + Coral references)
