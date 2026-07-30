# Meeting and Work Session Log

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
