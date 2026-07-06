# Meeting and Work Session Log

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
