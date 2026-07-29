# CLAUDE.md — BC Wildlife-Aware Dashcam

This file is the project brief for Claude Code (and any human) working in this
repo. It explains what the project is, why it exists, where it stands, what
remains, and the timeline. It is written to be self-contained: if you are a
fresh Claude Code session — for example running on the Raspberry Pi — read this
first and you have the whole picture.

Last updated: July 5, 2026.

---

## 1. Plain-language summary

A small computer mounts on a car windshield and watches the road. When an animal
is ahead, it recognises what kind it is (deer, moose, bear, elk, cougar, coyote,
raccoon), estimates how close it is, and warns the driver — a beep and a light
that grow more urgent the nearer the animal. Every sighting is saved with GPS
location and time, building the first species-level map of where wildlife crosses
BC highways.

## 2. Why it exists

ICBC recorded 12,519 wildlife-vehicle collisions in BC in 2024 — a high well
above the decade average of 11,600/yr, with 24 fatal collisions across
2015–2024. At 100 km/h a car needs 71 metres to stop on dry asphalt (assuming
a 1.0s reaction time and μ=0.9 braking grip — see docs/physics-references.md
for the full range, up to ~98m under more conservative assumptions). The
device must see, identify, and warn faster than a human could react and brake
inside that distance. That single requirement drives every design choice: **speed and
reliability come before perfect accuracy.** The research contribution is the
GPS-tagged wildlife-encounter dataset, which can be cross-referenced against
ICBC collision data.

## 3. What it does (system overview)

A single fine-tuned YOLOv8n model, quantised to INT8, runs on a Raspberry Pi 5
with a Hailo-8L AI accelerator (13 TOPS), doing real-time multi-class detection
with no internet dependency. Detections drive a three-tier driver warning and are
logged to the SD card in JSONL with GPS coordinates.

## 4. How it works (pipeline)

```
Camera ─► YOLOv8n INT8 on Hailo-8L ─► distance estimate ─► proximity zone
                                                              │
                              ┌───────────────────────────────┤
                              ▼                               ▼
                     driver alert (buzzer/LED/OLED)   SD log (GPS + species + zone)
```

Two-stage detection approach (per supervisor): animal *presence* first
(MegaDetector-style), species *classification* second (YOLOv8n).

Safety rules:
- **Approach-vector filter:** only warn for animals moving toward the car. A
  shrinking bounding box means it is leaving — no alert.
- **Highest-risk-only:** with several animals in frame, warn for the highest-risk
  one. All detections are still logged.

## 5. Hardware

| Component | Role | Status |
|---|---|---|
| Raspberry Pi 5 (8 GB) | Main computer | In hand, OS flashed |
| Hailo-8L AI Kit (M.2 HAT+, 13 TOPS) | Runs the model | In hand, verified working |
| Pi Camera Module (imx219 sensor) | Road camera | Connected Jul 29 — **not** the Module 3 NoIR originally planned; confirmed via `rpicam-still` EXIF (`Model: imx219`). No IR-cut/NoIR night sensitivity — flagged for Aditya to confirm whether this is the intended part or needs swapping. |
| u-blox NEO-M8N GPS | Location, speed, time | Ordering — only missing part |
| Active piezo buzzer | Primary audible alert | In hand |
| WS2812B RGB LED bar (GPIO 18) | Visual alert | In hand |
| SSD1306 OLED (I2C) | Species + distance readout | In hand |
| 12V→5V regulator | Car power | With Aditya |
| 64 GB SD card | Storage / OS | Flashed with Raspberry Pi OS Trixie |

## 6. Features — all retained, sequenced by build priority

No feature is dropped. They are ordered so the core safety loop works first and
the highest-risk additions come last. If time runs short, only the riskiest
extra slips, never the core. (See `docs/bc-dashcam-project-design.pdf`.)

**P1 — core loop (must work):**
- 7-class wildlife species detection
- Real-time INT8 inference on Hailo-8L
- Distance via apparent size (thin-lens: species shoulder height + focal length)
- Three-tier proximity alert (buzzer, LED, OLED)
- GPS-tagged SD logging (JSONL)
- Road test + validation metrics (mAP, false pos/neg)

**P2 — refinements:**
- Time-to-contact (TTC) optical-expansion distance, fused conservatively with
  thin-lens (`d_final = min(d_ttc, d_thin_lens)`)
- Adult-vs-child pedestrian sub-classification (head-to-body ratio)
- Vehicle-type classification (largely from the COCO base model)
- GPS speed-scaling of the zone thresholds

**P3 — built last (highest risk):**
- FLIR Lepton 3.5 thermal camera + fusion for night / low-visibility

Three-tier zones: **>80 m** log only · **40–80 m** amber pulse + two beeps ·
**<40 m** red flash + rapid beep + OLED shows species/distance.

## 7. The data & model flow (important — read before touching data)

```
SSD dataset (2,860 imgs) ─► train (Colab, GPU) ─► best.pt ─► quantise INT8
   (stays on SSD)                                   │        (Hailo DFC, 32GB RAM)
                                                     ▼
                                                model.hef ──► copy to Pi ──► run
```

- The **raw dataset never goes on the Pi.** It lives on the T7 SSD and is only
  used for training and for INT8 calibration, both on a bigger machine.
- **`best.pt` does not run on the Pi directly.** It must be compiled to Hailo's
  `.hef` INT8 format with the Hailo Dataflow Compiler (needs ~32 GB RAM — try a
  Colab high-RAM runtime first). Only the small `.hef` is copied to the Pi.
- `best.pt` is backed up in three places: T7 SSD (`models/run1-7class/best.pt`),
  Mac Downloads, and Google Drive.

## 8. Current status (July 5, 2026)

- **Phase 1 (data + docs): COMPLETE.** 3,015 images sourced, MegaDetector-filtered
  to 2,860 usable across 7 species. Dataset built locally into a 70/20/10 split
  (seed 42). YOLOv8n trained: **mAP50 0.823**, mAP50-95 0.638. Roboflow abandoned
  in favour of the local build pipeline. Docs, references, config all committed.
- **Phase 2 (hardware bench): IN PROGRESS — big milestone hit today.** Pi 5
  flashed with Raspberry Pi OS **Trixie** (64-bit), `hailo-all` installed, and the
  **Hailo-8L NPU verified working** (`hailortcli scan` finds it at `0001:01:00.0`,
  `fw-control identify` prints board info, PCIe Gen 3 enabled). Stock
  `hailo-rpi5-examples` detection demo run end-to-end on the bundled sample
  video — live window, bounding boxes, tracking IDs, ~30fps at 0% drop,
  confirmed via `hailortcli monitor` that the NPU (not CPU) does the
  inference. Along the way, fixed a real bug: the bundled C++ postprocess
  source doesn't compile against tappas-core 5.1.0 (`vstream_info()` was
  removed); fixed by symlinking tappas-core's own prebuilt equivalent.
  I2C enabled for the OLED (pending reboot).
- Camera and GPS not yet attached (arriving by Jul 8). While waiting on
  them, built and unit-tested (38 passing tests) all of `src/` that doesn't
  need either: config loaders, distance estimation (thin-lens + TTC fusion),
  zone classification, approach-vector filter, highest-risk selector, GPS
  NMEA parser, JSONL detection logger, and LED/OLED/buzzer alert drivers
  (those three are in hand but not yet physically wired — `simulate=True`
  mode lets the zone-to-output logic run and be tested without hardware).
  See `docs/meeting_log.md` (Jul 5 2026 entry) for the full writeup.

## 9. Development phases

| Phase | Goal | Status |
|---|---|---|
| 1 — Data + documentation | Dataset built, split, trained; docs | ✅ Complete |
| 2 — Hardware bench setup | Pi + Hailo + peripherals verified | 🔄 In progress |
| 3 — Training + quantisation | INT8 `.hef`, mAP acceptable | Not started |
| 4 — Full integration | Model on Hailo at target fps, all outputs, GPS logging | Not started |
| 5 — Validation | Road test, FP/FN rates, GPS × ICBC cross-ref | Not started |

## 10. Timeline (sprint)

- **Deadline sense:** core system + first road test by the **first week of
  August**; report written from the **2nd week of August onward** (build first,
  write after).
- **Jul 2–7 — prep gate (critical):** finish the Pi+Hailo bench (done today),
  collect camera + GPS + power from Aditya before he travels, lock a 32 GB compute
  option (Colab high-RAM). Getting every part in hand by **Jul 8** is the make-or-
  break.
- **Jul 8–19 — 10-day solo sprint** (Aditya travelling): pure software/integration.
  Quantise → first custom inference → distance/zones/alerts/GPS logging →
  end-to-end demo → first road test. Deepansh is in Vancouver Jul 12–14 but leaves
  late afternoon on the 12th, so Jul 12 morning is still workable.
- **Late July → first week Aug:** thermal camera (P3), second road test, refine.
- **Aug 10 onward:** analysis + report against real numbers.

## 11. Remaining work by area

- **Model:** INT8 quantise `best.pt` → `.hef` (Hailo DFC, 32 GB machine), measure
  float32→INT8 mAP drop, calibrate per-class confidence thresholds (account for
  lighting), export.
- **Deployment (Pi, `src/`):** camera capture → Hailo inference → detection parse;
  distance estimation (thin-lens then TTC fusion); proximity-zone logic;
  approach-vector filter; highest-risk selection; alert outputs (WS2812B LED,
  buzzer, SSD1306 OLED); JSONL SD logger; GPS ingest.
- **Hardware (Aditya):** acquire GPS, UART wiring + lock validation; 12V→5V rail;
  camera calibration (OpenCV checkerboard → `camera_matrix.npy`, `dist_coeffs.npy`)
  — hard dependency for distance estimation; vibration characterisation.
- **Validation:** Highway 97 road test day + night; FP/FN per class; GPS log ×
  ICBC data; document the camera-trap→dashcam domain shift.

## 12. Team & division

- **Deepansh Sabharwal** (Computer Engineering) — dataset, model, quantisation,
  Hailo deployment, distance/TTC, zone logic, logging, warning outputs.
- **Aditya Patel** (Electrical Engineering) — camera integration, GPS wiring,
  power, calibration, latency/vibration characterisation.
- **Supervisor:** Dr. Thomas Johnson, UBC Okanagan School of Engineering.

## 13. Key decisions & constraints

- **OS is Raspberry Pi OS Trixie (Debian 13), not Bookworm.** Hailo AI Kit gained
  full Trixie support in Dec 2025; Trixie is now the recommended OS. Install the
  stack with `sudo apt update && sudo apt full-upgrade -y` then
  `sudo apt install -y dkms hailo-all`, then reboot.
- Target: YOLOv8n INT8 on Hailo-8L, aiming ~80–120 fps.
- Quantisation (Hailo Dataflow Compiler) needs ~32 GB RAM — do it on Colab
  high-RAM or a cloud VM, not the 8 GB laptop.
- Supervisor requirements: two-stage pipeline, approach-vector, highest-risk
  alerting, confidence must account for lighting, validation via held-out test +
  road test.

## 14. Known limitations

- **Domain shift (externally flagged by the WiRE Lab, UBC Biology):** all training
  data is camera-trap / naturalist imagery, which differs from a dashcam
  viewpoint. Mitigation: collect road/dashcam-perspective frames
  (`scripts/extract-frames.py`) from the road tests and public footage; this is a
  documented limitation for the report, not a bug.
- Weakest classes: raccoon (mAP50-95 0.492) and elk (0.573); moose has the fewest
  images (316). Errors are background bleed, not cross-class confusion.

## 15. Repo structure

```
config/     alert-zones.yaml, species.yaml (shoulder heights, risk tiers)
docs/       development_phases, dataset_survey, interface_contract,
            gps_interface_spec, meeting_log, references.bib,
            phase2-kickoff, bc-dashcam-project-design.pdf
notebooks/  01 environment-check · 02 inaturalist-download ·
            03 megadetector-filtering · 04 yolov8-training
scripts/    build-yolo-dataset.py · sort-by-confidence.py · extract-frames.py
src/        deployment code (Phase 2+; currently a placeholder)
```

## 16. If you are Claude Code running on the Raspberry Pi

- This Pi **is the deployment target.** You'll help build the on-device software
  in `src/`: camera → Hailo inference → distance → zones → alerts → GPS logging.
- You do **not** need the dataset here. Only the finished `.hef` model ever lands
  on the Pi.
- The non-hardware-dependent half of `src/` is done (config, distance, zones,
  approach filter, risk selector, GPS parser, detection logger, alert
  drivers in `simulate` mode) — see `docs/meeting_log.md` Jul 5 2026 entry.
  Immediate remaining tasks: (1) physically wire LED bar/OLED/buzzer and run
  `scripts/test_{led_bar,oled,buzzer}.py` for real, (2) once the camera
  arrives, wire the Hailo `hailonet`/tracker detection metadata into
  `src/approach_filter.py` + `src/risk_selector.py` + `src/zones.py` to
  replace the stock `basic_pipelines/detection.py` callback.
- Hardware facts: Hailo-8L at `0001:01:00.0`, PCIe Gen 3, `hailo-all` installed.
- GPIO plan: WS2812B LED bar on GPIO 18; SSD1306 OLED on I2C; piezo buzzer on
  GPIO; u-blox GPS over UART (RX = GPIO 15), 3.3 V — **never 5 V**. Full
  physical wiring reference (exact pins, I2C setup, buzzer pin caveat):
  `docs/hardware-wiring.md`.
- Prefer the official Hailo examples and `rpicam-apps` + Hailo post-process paths.
- When you write deployment code, match it to the config in `config/` and the
  interface contracts in `docs/`.
