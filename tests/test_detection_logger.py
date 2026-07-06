import json

from src.detection_logger import DetectionLogger
from src.gps_parser import GpsFix


def test_log_writes_valid_jsonl(tmp_path):
    log_path = tmp_path / "detections.jsonl"
    logger = DetectionLogger(log_path)
    fix = GpsFix(utc_timestamp="2026-07-05T12:00:00Z", latitude=49.88, longitude=-119.44, speed_kmh=97.2)

    logger.log(species="moose", confidence=0.912345, zone_name="zone3", distance_m=12.345, gps_fix=fix, track_id=7)

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["species"] == "moose"
    assert record["confidence"] == 0.9123
    assert record["zone"] == "zone3"
    assert record["distance_m"] == 12.35
    assert record["track_id"] == 7
    assert record["gps"]["latitude"] == 49.88


def test_log_handles_missing_gps_fix(tmp_path):
    log_path = tmp_path / "detections.jsonl"
    logger = DetectionLogger(log_path)
    logger.log(species="deer", confidence=0.8, zone_name="zone1", distance_m=100.0, gps_fix=None)

    record = json.loads(log_path.read_text().splitlines()[0])
    assert record["gps"] is None


def test_log_appends_multiple_records(tmp_path):
    log_path = tmp_path / "detections.jsonl"
    logger = DetectionLogger(log_path)
    logger.log(species="deer", confidence=0.8, zone_name="zone1", distance_m=100.0, gps_fix=None)
    logger.log(species="bear", confidence=0.7, zone_name="zone2", distance_m=50.0, gps_fix=None)

    lines = log_path.read_text().splitlines()
    assert len(lines) == 2


def test_creates_parent_directory(tmp_path):
    log_path = tmp_path / "nested" / "dir" / "detections.jsonl"
    logger = DetectionLogger(log_path)
    logger.log(species="deer", confidence=0.8, zone_name="zone1", distance_m=100.0, gps_fix=None)
    assert log_path.exists()
