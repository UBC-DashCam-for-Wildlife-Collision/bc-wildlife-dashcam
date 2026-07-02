# Development Phases

**Model:** Incremental development with fixed review gates. Each phase has defined exit criteria that must be met before advancing to the next.

**Timeline:** 4 months, proof-of-concept phase.

---

## Phase 1 — Data and Documentation

**Objective:** Build the training dataset, establish all documentation, and get supervisor approval on the system design.

**Exit criteria:**
- All 7 wildlife species downloaded and filtered through MegaDetector v5a with confidence threshold >= 0.5
- Dataset uploaded to Roboflow with correct class labels and verified bounding box annotations
- Dataset version generated with 70/20/10 train/val/test split and Albumentations augmentation
- Held-out test set defined and isolated before any training begins
- Interface contract between Deepansh and Aditya committed to repo
- GPS interface specification committed to repo
- Dataset survey with source analysis and pull strategy committed to repo
- Pipeline decision tree diagram drawn and presented to Dr. Johnson
- Data flow diagram drawn and presented to Dr. Johnson

**Status as of July 2, 2026:** Complete. All 7 species downloaded and filtered (3,015 images, 2,860 usable). Dataset built locally into a 70/20/10 YOLOv8 split and trained (YOLOv8n, mAP50 0.823). Interface contract, GPS spec, dataset survey, and diagrams all done. Roboflow was dropped in favour of the local build, which removes the earlier class-label blocker entirely.

**What was completed in Phase 1:**

1. **Dataset sourcing.** Pulled images from iNaturalist BC and Caltech Camera Traps for all 7 species. Cougar required a global iNaturalist pull because BC-only observations (332) were insufficient for fine-tuning. Final usable counts after MegaDetector filtering: bear 421, cougar 348, coyote 450, deer 479, elk 449, moose 316, raccoon 397.

2. **MegaDetector filtering.** Every downloaded image was run through MegaDetector v5a. Only images with a detection confidence >= 0.5 were kept. This removed blurry, occluded, and empty images automatically. Raccoon required additional manual false-positive review.

3. **Dataset assembly.** Roboflow was initially trialled for annotation hosting, but the dataset is now built entirely locally via `scripts/build-yolo-dataset.py`, which reads the MegaDetector detection JSONs, keeps the highest-confidence detection per image, converts to YOLO format, and writes the train/valid/test split. Roboflow has been dropped from the pipeline.

4. **Documentation.** Dataset survey, interface contract, GPS interface spec, and meeting log all committed to the repo. Pipeline decision tree and data flow diagrams drawn on iPad and presented to Dr. Johnson at the May 20 meeting.

5. **External outreach.** Aditya contacted Dr. Ford's WiRE Lab (UBC Biology) regarding camera trap data sharing and validation footage. The WiRE Lab flagged a critical domain-shift risk: camera-trap imagery (fixed low-angle, IR night, broadside animals) will likely underperform when the model encounters real dashcam footage. This is now a documented limitation.

**Phase 1 is closed.** The dataset is built, split, and trained on. Dataset
expansion (raising per-species caps, adding road-perspective footage) continues
in parallel with later phases but does not block progress. See
[dataset_survey.md](dataset_survey.md) for the expansion plan.

---

## Phase 2 — Hardware Bench Setup

**Objective:** Get the Raspberry Pi 5, Hailo AI Kit, camera, and all peripherals physically assembled and verified working on the bench before any custom model deployment.

**Exit criteria:**
- Fresh 64-bit Raspberry Pi OS (Bookworm) flashed and booted on Pi 5
- Hailo-8L M.2 HAT+ physically installed and detected via `hailortcli fw-control identify`
- PCIe Gen 3.0 enabled and confirmed in `/boot/firmware/config.txt`
- HailoRT SDK, TAPPAS, and GStreamer pipeline dependencies installed
- Stock Hailo YOLOv8 demo running through the full NPU inference pipeline
- Camera Module 3 NoIR attached and streaming via `rpicam-hello`
- Live camera feed running through the Hailo demo pipeline
- WS2812B LED bar tested on GPIO 18 (amber pulse and red flash patterns)
- SSD1306 OLED display tested over I2C
- Piezo buzzer tested via GPIO

**Status as of June 25, 2026:** Not started. Begins June 26. Camera is with Aditya (pickup this weekend). GPS module not yet acquired.

---

## Phase 3 — Training and Quantization

**Objective:** Fine-tune YOLOv8n on the curated dataset, quantize to INT8, and validate that quantization does not unacceptably degrade accuracy.

**Exit criteria:**
- YOLOv8n fine-tuned on all 7 species with acceptable mAP on held-out test set
- INT8 quantized via Hailo Dataflow Compiler
- mAP degradation from float32 to INT8 measured and documented
- Confidence threshold calibrated per class on held-out test split
- Per-class precision, recall, and mAP50-95 documented
- Weights exported in Hailo HEF format ready for deployment

**Status as of June 25, 2026:** Not started. Depends on Phase 1 dataset version being finalized.

---

## Phase 4 — Full Hardware Integration

**Objective:** Deploy the quantized model onto the Hailo-8L and integrate all hardware subsystems into a functioning end-to-end prototype.

**Exit criteria:**
- Custom INT8 model running on Hailo-8L at target frame rate (80-120 fps)
- Distance estimation operational (thin lens + TTC optical expansion, conservative fusion)
- Three-tier proximity zone logic triggering correct alert responses
- All warning outputs functional: LED bar (amber pulse, red flash), buzzer (short beeps, continuous), OLED (species + distance)
- GPS logging verified: detection events written to SD card in JSONL format with coordinates, speed, species, confidence, zone
- Approach vector filtering confirmed (shrinking bounding box = retreating = no alert)
- Camera calibration completed (Aditya) for distance estimation

**Status as of June 25, 2026:** Not started. Depends on Phase 2 (hardware) and Phase 3 (model).

---

## Phase 5 — Validation

**Objective:** Validate the complete system in real-world conditions and document performance for the project report.

**Exit criteria:**
- Road test completed on BC Highway 97 corridor
- False positive and false negative rates documented per class
- GPS encounter log cross-referenced with ICBC wildlife-collision data
- Nighttime performance characterized (Camera Module 3 NoIR + IR)
- Vibration impact on detection confidence measured and documented
- Domain-shift limitation (camera-trap training data vs dashcam deployment) explicitly documented
- Final mAP, precision, recall reported on road-test data

**Status as of June 25, 2026:** Not started. Final phase.
