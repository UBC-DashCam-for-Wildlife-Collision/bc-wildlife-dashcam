# BC Wildlife-Aware Dashcam System

A windshield-mounted embedded device that performs real-time multi-class object detection and classification using a fine-tuned YOLOv8n INT8 model. Detects and classifies wildlife by species (deer, elk, moose, bear, cougar, coyote, raccoon), pedestrians by age group (adult vs child), and vehicles by type. All inference runs on-device with no internet dependency.

Detection events are logged with GPS coordinates, timestamp, species label, confidence score, and proximity zone to SD card in JSONL format, generating the first GPS-tagged, species-level wildlife encounter dataset for BC Highway 97.

## Why This Exists

ICBC reported 12,519 wildlife-vehicle collisions in BC in 2024, well above the decade average of 11,600 per year. 24 collisions were fatal across 2015-2024. At 100 km/h, a car needs 71-98 metres to stop on dry asphalt depending on reaction time and braking conditions (see [docs/physics-references.md](docs/physics-references.md)). This system has to detect, classify, and alert the driver faster than a human could react and brake inside that distance.

## Hardware

| Component | Spec |
|---|---|
| Raspberry Pi 5 | Quad-core ARM Cortex-A76 |
| Raspberry Pi AI Kit | Hailo-8L, 13 TOPS, M.2 HAT+ |
| Pi camera (imx219 sensor) | CSI-2; NoIR vs. standard variant unconfirmed, see CLAUDE.md |
| u-blox NEO-M8N GPS | UART, lat/lon/speed/UTC |
| Active piezo buzzer | GPIO-driven, primary alert |
| WS2812B RGB LED bar | GPIO 18, visual warning |
| SSD1306 OLED display | 128x64, I2C, species + distance readout |
| 12V to 5V power regulation | Vehicle power supply |
| MicroSD | 128GB High Endurance |

## Driver Warning System

Three-tier proximity zone system based on estimated distance to detected object:

| Zone | Range | Response |
|---|---|---|
| Zone 1 | > 80 m | Silent SD log only |
| Zone 2 | 40-80 m | Amber pulsing LED + two short beeps |
| Zone 3 | < 40 m | Red flashing LED + continuous rapid beep + OLED species/distance |

Approach vector filtering ensures alerts only trigger on animals moving toward the vehicle, not retreating. When multiple objects are detected in a single frame, the system alerts on the highest-risk class only. All detections are logged regardless of alert status.

## Development Phases

See [docs/development_phases.md](docs/development_phases.md) for the full phase breakdown with exit criteria.

## Repository Structure

```
bc-dashcam/
  config/
    alert-zones.yaml        # Three-tier proximity zone definitions
    species.yaml            # Species classes, shoulder heights, risk tiers
  docs/
    dataset_survey.md       # Species coverage, source analysis, pull strategy
    development_phases.md   # Five phases with exit criteria
    gps_interface_spec.md   # u-blox NEO-M8N UART config, NMEA parsing
    interface_contract.md   # Hardware/software interface definitions
    meeting_log.md          # Work session log with decisions and blockers
    references.bib          # Full citation bibliography
    bc-dashcam-project-design.pdf  # Simplified project design (plain-language)
  notebooks/
    01-environment-check.ipynb     # GPU and dependency verification
    02-inaturalist-download.ipynb  # Species image download pipeline
    03-megadetector-filtering.ipynb  # MegaDetector v5a bbox annotation
    04-yolov8-training.ipynb       # YOLOv8n fine-tuning on 7 classes
  scripts/
    build-yolo-dataset.py   # MegaDetector JSON -> YOLOv8 dataset + split
    sort-by-confidence.py   # Sort a species into usable/rejected by conf
    extract-frames.py       # Road/dashcam video -> frames (domain-matched data)
  src/                      # Deployment source code (Phase 2+)
  requirements.txt          # Python dependencies
  LICENSE                   # MIT
```

## Team

- **Deepansh Sabharwal**, Computer Engineering, UBC Okanagan
- **Aditya Patel**, Electrical Engineering, UBC Okanagan

## Supervisor

Dr. Thomas Johnson, School of Engineering, UBC Okanagan
