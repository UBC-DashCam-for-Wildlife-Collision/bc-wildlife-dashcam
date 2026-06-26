# Project Status Update — June 3, 2026

**Prepared for:** Dr. Thomas Johnson
**Prepared by:** Deepansh Sabharwal, Aditya Patel
**Project:** BC Wildlife-Aware Dashcam System

---

## Current Status: Phase 1 Complete, Phase 2 Starting

---

## Completed Work

### Dataset Pipeline (Deepansh)

All 7 target wildlife species have been downloaded and filtered through MegaDetector v5a.

**Final usable image counts (confidence >= 0.5):**

| Species | Downloaded | Usable | Usable Rate |
|---|---|---|---|
| Deer | 484 | 479 | 99.0% |
| Coyote | 473 | 450 | 95.1% |
| Elk | 471 | 449 | 95.3% |
| Raccoon | 454 | 397 | 87.4% |
| Bear | 437 | 421 | 96.3% |
| Cougar | 380 | 348 | 91.6% |
| Moose | 316 | 316 | 63.2% |
| **Total** | **3,015** | **2,860** | **94.9%** |

MegaDetector JSON annotations converted to YOLOv8 format locally via custom build script. Dataset split 70/20/10 (2,001 train / 572 val / 287 test), fixed seed 42 for reproducibility. Held-out test set defined and isolated before first training run, per supervisor requirement. Roboflow dependency removed; full dataset pipeline runs locally from source JSONs.

### Model Training (Deepansh)

YOLOv8n fine-tuned on all 7 species. Training configuration: 100 epochs, Tesla T4 GPU (Colab), batch size 32.

**Validation set results:**

| Metric | Value |
|---|---|
| mAP50 | 0.823 |
| mAP50-95 | 0.638 |
| Precision | 0.797 |
| Recall | 0.767 |

**Per-class mAP50-95:**

| Species | mAP50-95 |
|---|---|
| Cougar | 0.755 |
| Bear | 0.704 |
| Deer | 0.694 |
| Coyote | 0.660 |
| Moose | 0.588 |
| Elk | 0.573 |
| Raccoon | 0.492 |

Raccoon and elk are the weakest classes. Analysis shows recall bleed into background, not cross-class confusion. A low-confidence false positive was observed at 0.4 confidence, confirming that a confidence threshold floor is required in the alert logic.

Weights saved: `best.pt` (6.2 MB). Run logged to WandB project `bc-dashcam-yolov8`. Artifacts backed up to Google Drive.

### Infrastructure

- GitHub organization and private repo live with branch protection on main
- Interface contract, GPS interface spec, dataset survey, and meeting log committed
- Pipeline decision tree and data flow diagram drawn and presented at May 20 meeting

### Hardware (Aditya)

- All components ordered May 26
- Raspberry Pi 5, Hailo AI Kit, and Camera Module 3 NoIR arrived
- Remaining components arriving this week
- GPS module (u-blox NEO-M8N) not yet acquired — only missing part

---

## Development Phases

| Phase | Description | Status |
|---|---|---|
| Phase 1 — Data + Documentation | Dataset built, split defined, diagrams approved | Complete pending Roboflow fix |
| Phase 2 — Hardware Bench Setup | Pi 5 flashed, Hailo verified, camera confirmed, GPIO tested | Starting |
| Phase 3 — Training + Quantization | YOLOv8n fine-tuned, INT8 quantized, mAP acceptable | Not started |
| Phase 4 — Full Hardware Integration | Model on Hailo-8L, warning outputs functional, GPS logging | Not started |
| Phase 5 — Validation | Road test, FP/FN documented, GPS log cross-referenced with ICBC | Not started |

See `docs/development_phases.md` for full exit criteria per phase.

---

## Immediate Next Steps

1. **INT8 quantization** via Hailo Dataflow Compiler — measure mAP degradation against float32 baseline
2. **Confidence threshold calibration** on held-out test split — establish per-class alert floors
3. **Pi 5 bench setup** — OS flash, HailoRT SDK install, GPIO wiring for LED, buzzer, OLED
4. **GPS UART wiring and validation** (Aditya) — blocked until module is acquired
5. **Camera calibration** via OpenCV checkerboard (Aditya) — hard dependency for distance estimation
