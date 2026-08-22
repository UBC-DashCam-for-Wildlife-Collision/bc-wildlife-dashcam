# Full Session Summary — BC Wildlife-Aware Dashcam

**Covers one continuous working session spanning July 2 through August 17,
2026.** Written as a standalone narrative handoff for anyone who wasn't part
of the original conversation — a fresh Claude Code session, Aditya, or
Deepansh returning after time away. `CLAUDE.md` is the living, concise
project brief; this document is the fuller story of how the project got to
its current state, in order, with nothing skipped. `docs/meeting_log.md` has
per-day entries covering much of the same ground in more clinical form —
this document connects them into one narrative.

---

## 1. Starting point: documentation and repo engineering pass

The session opened with a full project handoff document (dataset status,
hardware inventory, team division, supervisor feedback) that became the
seed for a persistent memory system tracking the user's role, working
style, and project context across sessions.

From there, the repo itself got a full engineering-standards pass:

- Rewrote every doc in `docs/` for clarity and to close out Phase 1
  properly: `dataset_survey.md`, `interface_contract.md`,
  `gps_interface_spec.md` (moved out of `notebooks/`, where it didn't
  belong), `meeting_log.md`, plus a new `development_phases.md` covering
  all five phases with real exit criteria.
- Rebuilt the README, added `.gitignore`, an MIT `LICENSE`,
  `requirements.txt`, and `docs/references.bib` (30+ citations pulled from
  the original handoff doc).
- Replaced four messy, underscore-named notebooks with clean,
  output-stripped, hyphen-named versions:
  `01-environment-check.ipynb` through `04-yolov8-training.ipynb`.
- Added `scripts/build-yolo-dataset.py` (the actual canonical dataset
  builder, previously only living in Downloads), `sort-by-confidence.py`,
  and `extract-frames.py` for future road-perspective data collection.
- Config-as-code: `config/species.yaml` (shoulder heights, risk tiers) and
  `config/alert-zones.yaml` (three-tier zone definitions).

A real security issue was caught and fixed during this pass: a Roboflow API
key was hardcoded in plaintext in an old script sitting in Downloads. It was
removed from any committed code and the user was told to rotate the key —
**this should be double-checked as actually done, it was flagged but not
confirmed resolved.**

## 2. Project redesign: scope, not features, cut

With roughly six and a half weeks left before the informal deadline, the
project was reorganized into build-priority tiers rather than dropped
features, per explicit instruction that nothing gets cut:

- **P1 (core loop):** 7-class detection, real-time Hailo inference,
  thin-lens distance, three-tier alerts, GPS-tagged logging, road test.
- **P2 (refinements):** TTC distance fusion, pedestrian sub-classification,
  vehicle-type classification, GPS speed-scaling of zones.
- **P3 (built last, highest risk):** FLIR Lepton thermal camera fusion.

This is documented in `docs/bc-dashcam-project-design.pdf`, a plain-language
design doc built specifically so nothing reads as "dropped," only
sequenced. `docs/phase2-kickoff.md` captured the day-by-day Phase 2 task
breakdown that followed.

## 3. Phase 2: hardware bring-up on the Pi

The Raspberry Pi 5 + Hailo-8L bench setup happened over several sessions:

- Flashed Raspberry Pi OS **Trixie**, not Bookworm as the original plan
  said — verified that Hailo AI Kit support landed on Trixie in December
  2025 and it's now the recommended OS.
- Installed the Hailo stack (`hailo-all`), verified the NPU via
  `hailortcli scan` (found at `0001:01:00.0`) and `fw-control identify`.
  PCIe Gen 3 enabled.
- Ran the stock `hailo-rpi5-examples` detection demo end-to-end, ~30fps at
  0% frame drops, confirmed via `hailortcli monitor` that the NPU (not the
  CPU) did the inference. Along the way, fixed a real toolchain bug: the
  bundled C++ postprocess source didn't compile against the installed
  tappas-core 5.1.0 (`vstream_info()` had been removed upstream) — fixed by
  symlinking tappas-core's own prebuilt equivalent.
- Got Claude Code running natively on the Pi itself (native installer,
  meets all listed system requirements), with `CLAUDE.md` written
  specifically so a fresh Pi session has full context without re-briefing.
- Worked through a real GitHub auth headache on the Pi (SSH key vs HTTPS,
  2FA blocking `gh auth login` on the Pi's browser, eventually resolved via
  a Personal Access Token generated on the Mac's already-authenticated
  Safari session and pasted into `gh auth login` on the Pi).
- Wrote `docs/hardware-wiring.md` with exact pin references for the LED
  bar (GPIO18), OLED (I2C), and buzzer (GPIO17, flagged as an unconfirmed
  placeholder pending physical wiring).
- Built and unit-tested (38 passing tests) the entire hardware-independent
  half of `src/`: config loaders, thin-lens + TTC distance estimation,
  zone classification, approach-vector filter, highest-risk selector, GPS
  NMEA parser, JSONL detection logger, and LED/OLED/buzzer alert drivers,
  all runnable in `simulate=True` mode without hardware attached.

## 4. Hardware procurement: GPS module

A genuinely tricky mini-saga: the market is full of GPS modules mislabeled
as "NEO-M8N" that are actually relabeled NEO-6M boards, or use invented
part numbers like "NEO-8M" (which doesn't exist in u-blox's real lineup —
their naming goes NEO-6M/7M, then NEO-**M8N** from generation 8 onward).
Walked through several listings; the one that actually checked out was a
Carhar NEO-M8N module confirmed via a visible chip marking
(`NEO-M8N-0-01`) in the product photos and correct multi-constellation
spec claims (GPS/QZSS/GLONASS/BeiDou/Galileo). Also flagged a real shipping
risk (the listing's delivery window landed after the sprint's key dates)
and suggested decoupling the road test's detection-validation goal from its
GPS-logging goal so a GPS delay doesn't block the whole test.

**As of the most recent status, GPS is still the only hardware component
not confirmed in hand.**

## 5. Camera troubles

Two separate camera problems surfaced:

- **Ribbon cable compatibility.** The Pi 5 uses a 22-pin CSI connector,
  different from the 15-pin connector on older Pi boards, so the cable that
  shipped with the Camera Module 3 didn't fit. Generic FFC/FPC ribbon
  cables (uxcell listings) were evaluated and rejected — contact
  orientation (same-side vs opposite-side, sometimes labeled "Type A" vs
  "Type B") isn't something a spec sheet reliably states, and getting it
  wrong means a cable that physically fits but transmits nothing. Officially
  Pi-5-specific cables were recommended instead.
- **A faulty camera unit** had to be returned entirely, causing a real
  multi-day delay that was disclosed honestly in an email to Dr. Johnson
  (see section 7).
- **Camera identity is still unresolved.** EXIF data from `rpicam-still`
  reported `Model: imx219` and was initially read as "not the Module 3
  NoIR originally planned." Later, a live preview under indoor lighting
  showed a magenta/pink color cast — the classic symptom of *no* IR-cut
  filter, i.e. evidence pointing the other way. EXIF's model tag can't
  actually distinguish the NoIR and standard variants (same sensor chip,
  different lens filter), so neither claim is settled. This needs a
  physical check (the module usually has "NoIR" printed on it) or an IR
  remote test, and it directly affects any future nighttime-range claims.
  **Do not treat either earlier note in `CLAUDE.md`'s hardware table as
  resolved.**

## 6. Supervisor engagement

Prepared a reading list for Dr. Johnson (Beery et al.'s domain-shift and
MegaDetector papers, the INT8 quantization paper, the YOLO paper — all
verified against real arXiv IDs before sending, since a wrong citation in
an email to a supervisor is not the place to guess), talking points for a
progress meeting framed around genuine engineering wins (the Hailo NPU
milestone, the toolchain bug fix, catching two of the project's own
headline statistics being subtly wrong — the "24 fatal collisions" figure
turned out to be a 2015-2024 cumulative total, not 2024-specific, and the
"71m stopping distance" figure sits at the optimistic end of a real range).

A camera-delay update email was also drafted and sent, disclosing the
faulty-unit replacement honestly rather than downplaying it, while leading
with the real technical progress made in parallel (the NPU verification,
the toolchain fix, the fully-tested hardware-independent `src/` code) —
framed as "blocked on hardware, not on judgment."

## 7. Phase 3, part one: first successful INT8 compile

This was the largest single technical effort of the session. Full detail
lives in `docs/meeting_log.md`'s July 29-30 entry; the short version:

- Set up Colab Pro (High-RAM + T4 GPU), built an isolated `hailo_env`
  (Miniconda, Python 3.10, since Hailo's Dataflow Compiler only ships for
  3.10, not Colab's default 3.12).
- Hit and diagnosed a real file-corruption issue: a 524MB wheel upload via
  Colab's direct browser widget silently truncated to ~174MB and produced
  a corrupted zip. Fixed by routing large transfers through Drive instead,
  and by adopting a strict discipline of verifying exact byte counts (not
  rounded sizes) after every transfer for the rest of the session.
- Exported `best.pt` to ONNX, parsed to a Hailo HAR.
- **The real blocker:** Hailo's automatic postprocess-extraction feature
  parsed and quantized fine but **failed to compile twice**
  (`Agent infeasible` / `No valid partition found`), even after fixing the
  optimization level with a GPU — proving the problem was structural, not
  a quantization-quality issue.
- **The fix:** parsed with explicit `--end-node-names` at the six raw
  per-stride conv outputs, matching Hailo's own official `yolov8n.alls`
  reference pattern (fetched directly from `hailo-ai/hailo_model_zoo` on
  GitHub) instead of relying on auto-extraction. Built a custom
  `nms_postprocess` JSON config with `"classes": 7` instead of the
  reference's 80. Verified via `hailo har info --verbose` that the internal
  layer names Hailo assigned (`conv41/42`, `conv52/53`, `conv62/63`)
  exactly matched the official reference's numbering — strong confirmation
  the architecture translated correctly.
- Result: first successful compile, 14 seconds, at a modest optimization
  level (401-image calibration set, GPU present but Bias-Correction-only
  quantization, since the calibration set was below Hailo's recommended
  1,024 images).
- The resulting `.hef` was committed directly to the repo at
  `models/bc_dashcam_yolov8n.hef` — a deliberate, documented exception to
  the general "no model weights in git" `.gitignore` policy, specifically
  so the Pi (no reliable Drive access) can `git pull` the deploy artifact
  directly.

## 8. Aug 2: label-indexing bug found and fixed

A same-day Pi session wired the compiled `.hef` into a real detection
pipeline (`scripts/run_wildlife_detection.py`, replacing `hailo_apps`'
stock COCO callback) and left an open-issues doc for the Mac side. The
most important finding: `config/hailo_labels.json` had a spurious
`"unlabeled"` class at index 0, guessed from an unrelated reference file
on the Pi (`barcode-labels.json`, a different model's convention).

This was fixed with certainty, not a guess: the actual `nms_postprocess`
config built the day before was reconstructed exactly (it had never been
committed) and confirmed to have **no** unlabeled/background offset —
network output index 0-6 maps directly to bear/cougar/coyote/deer/elk/
moose/raccoon, matching `scripts/build-yolo-dataset.py`'s alphabetical
0-indexed class list. `config/hailo_labels.json` was corrected, and the
compile config itself (`models/nms_config_7class.json`,
`models/bc_dashcam_yolov8n.alls`) was committed to the repo so this
never has to be reconstructed from memory again.

Also from that session: `scripts/calibrate_camera.py` was written ahead of
need (OpenCV checkerboard -> `camera_matrix.npy`/`dist_coeffs.npy` -> focal
length in px), and the camera-identity contradiction from section 5 was
first surfaced.

## 9. Phase 3, part two: the real max-optimization compile

Picked up again to properly finish what part one left incomplete. The
401-image calibration set and Bias-Correction-only quantization were a
known compromise — Hailo's `finetune` and `adaround` post-quantization
algorithms both default to a `dataset_size` of 1,024/256 respectively (this
was verified against Hailo's own documentation, not assumed), which is
exactly why the earlier warning cited "1,024" as a threshold.

- Rebuilt the calibration set from **all 2,001 training images** (up from
  401), still training-split-only per the existing rule about not touching
  the held-out test set. The resulting 1.1GB zip was uploaded through
  Drive from the start this time, having already learned that lesson.
- Re-ran `optimize` with the larger set: optimization level 2 was selected
  automatically (no "reducing level" warning this time), and
  **Quantization-Aware Fine-Tuning actually ran** — 4 real epochs, 128
  steps each, ~8m14s, superseding the earlier Bias-Correction-only result.
- Re-ran `compiler` with `compiler_optimization_level=max`. This took
  roughly five hours of wall-clock time (mostly unattended), searching 133
  different partition strategies before settling on a 3-context split.
  Two earlier attempts at this same max-optimization run had failed —
  once to what looked like an accidental interrupt, once to a Colab VM
  reset during an unattended gym trip — so this was genuinely the third
  attempt at getting a complete run. It finished cleanly this time,
  including surviving one live browser-tab disconnect/reconnect mid-run
  without losing progress (the underlying compute kept running
  server-side, a useful distinction from an actual VM reset).
- **Result: `"Successful Compilation"`** — the real max-optimization
  `.hef`, genuinely fine-tuned, replacing the July 30 compromise version.
  Same filename (`bc_dashcam_yolov8n.hef`), so it overwrote the Drive copy;
  the repo's committed copy was subsequently re-downloaded, verified by
  checksum, and re-committed to match.

## 10. LinkedIn content

Several rounds of drafting for a Phase 3 progress post, converging on: two
short, standalone posts (LinkedIn doesn't support multiple videos per post,
and there are two distinct videos — one of the physical hardware setup, one
of the live screen+LED test run) rather than one long post, each run
through a "humanizer" pass to strip AI-writing patterns (em dashes, rule-
of-three list cadences, generic closers) and add genuine first-person
voice. A factual error introduced during one smoothing pass — implying the
camera-hijacking bug caused the GPIO conflict bug, when they were actually
unrelated — was caught and corrected before finalizing. Character counts
were checked against real 2026 LinkedIn algorithm research (dwell time,
hashtag relevance, native video handling) rather than assumed.

**Both posts are drafted and ready; not yet confirmed posted.**

## 11. Checkerboard calibration prep

Walked through building a real calibration checkerboard: sourcing the
official OpenCV 9x6-internal-corner pattern (verified via their own docs
to be A4-sized, 210mm x 297mm), the internal-corners-vs-squares distinction
that trips people up (9x6 corners = 10x7 actual squares), print-scaling
discipline (100%/Actual Size, not "fit to page," since scaling silently
invalidates the square-size assumption), and mounting it flat and rigid on
foam board or similar backing.

## 12. Today (Aug 17): the in-car test

Full detail in `docs/car-test-2026-08-17-handoff.md`, which supersedes the
narrower `docs/pi-session-handoff-2026-08-17.md`. Summary:

- The printed checkerboard was verified correct by physically counting
  squares (7x10, matching the 9x6-corner spec) and measuring 23mm per
  square — checks out against the A4 math.
- Pre-drive hardware check passed: camera, LED bar, buzzer, OLED all
  individually confirmed. The OLED dropped off I2C again (the same
  recurring loose-connector issue first seen Aug 12) but was reseated and
  confirmed working before departure.
- Power: running off a cigarette-lighter USB charger for this test, not
  the final regulator. Confirmed clean (`vcgencmd get_throttled` = `0x0`)
  before leaving.
- `scripts/capture_calibration_photos.py` was written specifically for
  this session — auto-captures 20 photos with an audible terminal-bell
  countdown, so calibration photos can be taken hands-free over SSH with
  no screen needed. One real bug was found and fixed during testing: an
  initial fixed `--shutter` value produced solid-black frames in low
  light; switched to `--exposure sport --awb daylight` instead.
- **The session stalled at connectivity, not at the actual test.** After
  the camera was mounted in its final position (likely moving the car out
  of range of whatever it was previously connected to), Termius on the
  phone could not reconnect to the Pi over the phone's hotspot. Full
  troubleshooting tree is in the handoff doc: check the phone's own
  hotspot connected-devices list first (tells you whether the Pi joined
  the network at all), try the direct IP rather than relying on `.local`
  mDNS resolution over a hotspot, watch for a silently-blocking
  host-key-changed warning in Termius, and check for AP/client isolation
  on the phone if the Pi isn't listed at all.
- **As of this summary, the connectivity issue's resolution is unknown —
  the calibration capture, the calibration run, and the live detection
  test have not yet happened today.**
- A durable fix was proposed for future field sessions (not attempted
  today, needs to happen with normal Pi access first): set the Pi up as
  its own WiFi access point (`hostapd` + `dnsmasq`) so it always has a
  fixed, known IP, rather than depending on successfully rejoining
  whatever network happens to be available in the field.

---

## Where things actually stand right now

**Model:** Fully quantized and compiled at max optimization,
`models/bc_dashcam_yolov8n.hef` in the repo, label indexing verified
correct. The float32-vs-INT8 mAP drop still hasn't been measured — this
remains the single biggest open number for interpreting any accuracy
results.

**Hardware:** Pi 5 + Hailo-8L fully verified. Camera physically working but
its exact identity (NoIR or not) is unresolved. LED/buzzer/OLED all
individually tested; OLED has a recurring physical connector issue not yet
permanently fixed. GPS module still not in hand.

**Software:** Full detection pipeline (`scripts/run_wildlife_detection.py`)
wired up and running on real hardware, including live alert outputs.
Camera calibration script ready but has not yet produced a real
`camera_matrix.npy`/focal length — today's session was meant to be the
first time that happens, and got blocked before it could.

**Immediate next step, the moment Pi connectivity is restored:** clear the
junk test photos in `~/calibration_photos/`, run the real 20-photo capture,
run `calibrate_camera.py`, and finally run the live pipeline with a real
focal length instead of the placeholder value that's made every prior
distance/zone reading meaningless.

**Not yet done, in rough priority order:** finish today's calibration and
first live-road test; measure the mAP drop from quantization; resolve the
camera NoIR question with a physical check; permanently fix the OLED
connector; acquire the GPS module; set up the Pi as its own access point
for field reliability; post the two drafted LinkedIn updates; confirm the
Roboflow API key rotation actually happened.
