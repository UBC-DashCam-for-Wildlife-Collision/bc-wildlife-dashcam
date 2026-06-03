# Project Status Update - June 3, 2026
Prepared for: Dr. Thomas Johnson
Prepared by: Deepansh Sabharwal, Aditya Patel

## Current Status: Month 1, Week 4 - On Track

---

## Completed to Date

### Infrastructure
- GitHub organization and private repo live (ubco-dashcam/bc-wildlife-dashcam)
- Branch protection on main, both contributors active
- Interface contract, GPS interface spec, dataset survey, meeting log documented and committed
- Pipeline decision tree and data flow diagram drawn and presented May 20

### Dataset Pipeline (Deepansh)
- All 7 species downloaded and filtered through MegaDetector v5a
- Final usable counts: bear 421, cougar 348, coyote 450, deer 479, elk 449, moose 316, raccoon 397 — total 2,860
- MegaDetector JSON annotations converted to YOLOv8 format locally via custom build script
- Dataset split 70/20/10 (2001 train / 572 val / 287 test), fixed seed 42 for reproducibility
- Held-out test set defined and isolated before first training run per supervisor requirement
- Roboflow dependency removed; full dataset pipeline runs locally from source JSONs

### Model Training (Deepansh)
- YOLOv8n fine-tuned on all 7 species, 100 epochs, T4 GPU, batch 32
- Results on held-out validation set:
  - mAP50: 0.823
  - mAP50-95: 0.638
  - Precision: 0.797
  - Recall: 0.767
- Per-class mAP50-95: bear 0.704, cougar 0.755, coyote 0.660, deer 0.694, elk 0.573, moose 0.588, raccoon 0.492
- Raccoon and elk identified as weakest classes — recall bleed into background, not cross-class confusion
- Low-confidence false positive observed (0.4 confidence) — confirms confidence threshold floor required in alert logic
- Weights saved: best.pt (6.2 MB), run logged to wandb bc-dashcam-yolov8
- Run artifacts backed up to Google Drive

### Hardware (Aditya)
- All components ordered May 26
- Pi 5, Hailo AI Kit, Camera Module 3 NoIR arrived
- Remaining components arriving this week

---

## Phase Status

| Phase | Exit Criterion | Status |
|---|---|---|
| Phase 1 — Data + Documentation | Dataset built, split defined, diagrams approved | Complete pending approval |
| Phase 2 — Training + Quantization | YOLOv8n fine-tuned, INT8 quantized, mAP acceptable | Training complete, quantization upcoming |
| Phase 3 — Hardware Deployment | Model on Hailo-8L, warning outputs functional, GPS logging verified | In progress |
| Phase 4 — Validation | Road test complete, FP/FN documented, GPS log cross-referenced | Upcoming |

---

## Immediate Next Steps

- INT8 quantization via Hailo Dataflow Compiler, measure mAP degradation against float32 baseline
- Confidence threshold calibration on held-out test split, establish per-class alert floors
- Pi OS flash, HailoRT SDK install, GPIO output wiring (LED, buzzer, OLED)
- GPS UART wiring and validation (Aditya)
- Camera calibration via OpenCV checkerboard (Aditya) — hard dependency for distance estimation
