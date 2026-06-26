# BC Wildlife-Aware Dashcam System

A windshield-mounted embedded device that performs real-time multi-class object detection and classification using a fine-tuned YOLOv8n INT8 model. Detects and classifies wildlife by species (deer, elk, moose, bear, cougar, coyote, raccoon), pedestrians by age group (adult vs child), and vehicles by type. All inference runs on-device with no internet dependency.

Detection events are logged with GPS coordinates, timestamp, species label, confidence score, and proximity zone to SD card in JSONL format, generating the first GPS-tagged, species-level wildlife encounter dataset for BC Highway 97.

## Why This Exists

ICBC reported 12,519 wildlife-vehicle collisions in BC in 2024, a record high with 24 fatal incidents. Stopping distance at 100 km/h on dry asphalt is 71 metres. This system must detect, classify, and alert the driver faster than human reaction time allows for braking inside that envelope.

## Hardware

| Component | Spec |
|---|---|
| Raspberry Pi 5 | Quad-core ARM Cortex-A76 |
| Raspberry Pi AI Kit | Hailo-8L, 13 TOPS, M.2 HAT+ |
| Pi Camera Module 3 NoIR | Sony IMX708, CSI-2, IR night vision |
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

## Documentation

| Document | Description |
|---|---|
| [docs/development_phases.md](docs/development_phases.md) | Five development phases with exit criteria |
| [docs/dataset_survey.md](docs/dataset_survey.md) | Species coverage, source analysis, pull strategy |
| [docs/interface_contract.md](docs/interface_contract.md) | Hardware/software interface definitions between team members |
| [docs/gps_interface_spec.md](docs/gps_interface_spec.md) | u-blox NEO-M8N UART config, NMEA parsing, output format |
| [docs/meeting_log.md](docs/meeting_log.md) | Work session log with decisions and blockers |
| [docs/professor_update_june03.md](docs/professor_update_june03.md) | Status report prepared for Dr. Johnson |

## Team

- **Deepansh Sabharwal** — Computer Engineering, UBC Okanagan
- **Aditya Patel** — Electrical Engineering, UBC Okanagan

## Supervisor

Dr. Thomas Johnson, School of Engineering, UBC Okanagan
