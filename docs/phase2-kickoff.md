# Phase 2 Kickoff — Hardware Bench Setup

**Date:** June 26, 2026
**Prepared by:** Deepansh Sabharwal, Aditya Patel
**Status:** Phase 1 complete, Phase 2 beginning

---

## Phase 1 Exit Summary

All Phase 1 exit criteria have been met except one Roboflow UI issue that does not block Phase 2.

### Completed
- 3,015 images downloaded across 7 BC wildlife species (iNaturalist BC + Caltech Camera Traps)
- MegaDetector v5a filtering applied: 2,860 usable images at confidence >= 0.5
- Per-species usable counts: deer 479, coyote 450, elk 449, bear 421, raccoon 397, cougar 348, moose 316
- Cougar global pull completed (BC-only count of 332 was insufficient)
- Raccoon manual false-positive review completed
- YOLOv8n fine-tuned on all 7 classes: mAP50 0.823, mAP50-95 0.638, precision 0.797, recall 0.767
- Weakest classes identified: raccoon (0.492 mAP50-95) and elk (0.573), both background bleed not cross-class confusion
- Dataset split locked: 70/20/10 (2001/572/287), seed 42
- Held-out test set isolated before first training run
- Pipeline decision tree and data flow diagrams drawn and approved by Dr. Johnson
- Interface contract, GPS interface spec, dataset survey, and meeting log committed
- Full citation bibliography committed (30+ references)
- Species config and alert zone config committed as YAML
- Repository restructured to engineering standards: .gitignore, LICENSE, requirements.txt, clean notebooks

### Not completed (does not block Phase 2)
- Roboflow class-label "?" bug: annotations display placeholder labels instead of species names. Likely need to pre-create class names in the Roboflow project settings before upload. Will fix when convenient.

### Known limitations carried forward
- Domain shift risk: entire dataset is camera-trap style imagery, dashcam viewpoint will differ. Flagged by WiRE Lab (UBC Biology). Must be documented in formal report.
- Moose has the lowest image count (316) and lowest usable rate (63.2%). May need augmentation or supplementary data from LILA BC / iWildCam.

---

## Phase 2 Objective

Get the Raspberry Pi 5, Hailo AI Kit, camera, and all peripherals physically assembled and verified working on the bench before any custom model deployment.

---

## Phase 2 Task Breakdown

### Day 1 — June 26 (Deepansh, no camera needed)

| Step | Task | Verification |
|---|---|---|
| 1 | Flash 64-bit Raspberry Pi OS (Bookworm) onto 128GB MicroSD | Boot to desktop |
| 2 | Configure SSH and WiFi | SSH in from laptop |
| 3 | Full system update, firmware check | `uname -a`, firmware date post-Dec 2023 |
| 4 | Power off, install Hailo M.2 HAT+ into PCIe slot | Physical install |
| 5 | Enable PCIe Gen 3.0 in /boot/firmware/config.txt | Reboot, check dmesg |
| 6 | Install Hailo stack (firmware, HailoRT, TAPPAS, OpenCV, GStreamer) | Package install completes |
| 7 | Verify Hailo detection | `hailortcli fw-control identify` returns device info |
| 8 | Run stock Hailo YOLOv8 demo (no camera, file-based) | Inference output with bounding boxes |

### Weekend — June 28-29 (Deepansh + Aditya)

| Step | Task | Verification | Owner |
|---|---|---|---|
| 9 | Attach Camera Module 3 NoIR | `rpicam-hello -t 0` shows live feed | Deepansh |
| 10 | Live camera through Hailo demo pipeline | Real-time inference on camera feed | Deepansh |
| 11 | WS2812B LED bar on GPIO 18 | Amber pulse (0.3s) and red flash (0.1s) patterns | Deepansh |
| 12 | SSD1306 OLED over I2C | Text renders on display | Deepansh |
| 13 | Piezo buzzer via GPIO | Two-short-beep and continuous-rapid patterns | Deepansh |
| 14 | Camera calibration (OpenCV checkerboard) | camera_matrix.npy and dist_coeffs.npy generated | Aditya |

### Aditya — parallel

| Task | Status |
|---|---|
| Acquire u-blox NEO-M8N GPS module | Not yet acquired, only missing hardware |
| GPS UART wiring and validation | Blocked until module acquired |
| Follow up with Melissa / WiRE Lab | Pending |

---

## Phase 2 Exit Criteria

All of the following must be true before advancing to Phase 3:

- [ ] Pi 5 boots Bookworm, SSH works, system fully updated
- [ ] Hailo-8L detected via hailortcli and dmesg
- [ ] PCIe Gen 3.0 confirmed enabled
- [ ] Stock Hailo YOLOv8 demo runs successfully
- [ ] Camera Module 3 NoIR streams live video
- [ ] Live camera feed runs through Hailo inference pipeline
- [ ] WS2812B LED bar produces amber pulse and red flash patterns
- [ ] SSD1306 OLED displays text
- [ ] Piezo buzzer produces two-short and continuous-rapid patterns
- [ ] Camera calibration files delivered (camera_matrix.npy, dist_coeffs.npy)

---

## Hardware on Hand

| Component | Location | Ready |
|---|---|---|
| Raspberry Pi 5 | Deepansh | Yes |
| Hailo-8L AI Kit (M.2 HAT+) | Deepansh | Yes |
| Camera Module 3 NoIR | Aditya | Pickup Sat/Sun |
| u-blox NEO-M8N GPS | Not acquired | No |
| WS2812B LED bar | Deepansh | Yes |
| SSD1306 OLED | Deepansh | Yes |
| Piezo buzzer | Deepansh | Yes |
| 128GB MicroSD | Deepansh | Yes |
| 12V to 5V regulation | Aditya | Yes |

---

## Risk Items

1. **Hailo M.2 HAT+ compatibility:** First physical install. If the HAT+ does not seat correctly or PCIe negotiation fails, this blocks everything. Hailo community forums and hailo-ai/hailo-rpi5-examples are the fallback references.

2. **Camera Module 3 NoIR pickup:** If Aditya cannot deliver the camera this weekend, steps 9-10 and 14 slip to the following week. Steps 1-8 and 11-13 are unaffected.

3. **GPS module acquisition:** Continues to be the only missing hardware. Does not block Phase 2, but blocks Phase 4 (GPS logging and speed-based zone scaling).
