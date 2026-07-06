"""JSONL detection logger, per README.md: 'Detection events are logged with
GPS coordinates, timestamp, species label, confidence score, and proximity
zone to SD card in JSONL format.'

All detections are logged regardless of alert status (approach-vector /
highest-risk filtering only affects what triggers buzzer/LED/OLED, not what
gets written here).
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.gps_parser import GpsFix


class DetectionLogger:
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        species: str,
        confidence: float,
        zone_name: str,
        distance_m: float,
        gps_fix: GpsFix | None,
        track_id: int | None = None,
    ) -> None:
        record = {
            "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "species": species,
            "confidence": round(confidence, 4),
            "zone": zone_name,
            "distance_m": round(distance_m, 2),
            "track_id": track_id,
            "gps": asdict(gps_fix) if gps_fix is not None else None,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
