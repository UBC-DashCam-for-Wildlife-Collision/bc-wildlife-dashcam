#!/usr/bin/env python3
"""Wires the compiled wildlife .hef into the Hailo detection pipeline.

Run with the hailo-rpi5-examples venv (has gi/GStreamer, the `hailo` Python
bindings, and hailo_apps) -- not this repo's own venv:

    source ~/hailo-rpi5-examples/venv_hailo_rpi_examples/bin/activate
    python3 scripts/run_wildlife_detection.py -i rpi

Replaces hailo_apps' stock detection.py callback (COCO labels, no
zone/alert logic) with this project's actual pipeline: approach-vector
filter -> highest-risk selection -> distance -> zone -> alert, per
CLAUDE.md sections 4 and 16.

Label indexing (config/hailo_labels.json) was verified 2026-08-02 against
the actual compile config, models/nms_config_7class.json + models/
bc_dashcam_yolov8n.alls (reconstructed from the Colab session that produced
this .hef -- see docs/meeting_log.md, Aug 2 entry): no "unlabeled" class 0,
network output index 0-6 maps directly to bear/cougar/coyote/deer/elk/
moose/raccoon, matching scripts/build-yolo-dataset.py's alphabetical
0-indexed class list. hailo_labels.json has been corrected to drop the
"unlabeled" entry it previously had at index 0.

One known gap -- read before trusting this script's output:

1. FOCAL_LENGTH_PX_PLACEHOLDER below is NOT a real calibration value --
   Aditya's checkerboard calibration (camera_matrix.npy, per
   docs/interface_contract.md) hasn't happened yet. Distances/zones out of
   this script aren't trustworthy until that lands; override with
   --focal-length-px once it does.
"""

import argparse
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import gi  # noqa: E402

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

import hailo  # noqa: E402
from hailo_apps.hailo_app_python.apps.detection.detection_pipeline import GStreamerDetectionApp  # noqa: E402
from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad  # noqa: E402
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class  # noqa: E402

from src.alerts.buzzer import Buzzer  # noqa: E402
from src.alerts.controller import AlertController  # noqa: E402
from src.alerts.led_bar import LedBar  # noqa: E402
from src.alerts.oled_display import OledDisplay  # noqa: E402
from src.approach_filter import ApproachTracker  # noqa: E402
from src.config import load_species_table, load_zone_table  # noqa: E402
from src.detection_logger import DetectionLogger  # noqa: E402
from src.distance import thin_lens_distance_for_species  # noqa: E402
from src.risk_selector import Detection as RiskDetection  # noqa: E402
from src.risk_selector import select_alert_detection  # noqa: E402
from src.zones import classify_zone  # noqa: E402

DEFAULT_HEF_PATH = REPO_ROOT / "models" / "bc_dashcam_yolov8n.hef"
DEFAULT_LABELS_JSON = REPO_ROOT / "config" / "hailo_labels.json"
DEFAULT_LOG_PATH = REPO_ROOT / "logs" / "detections.jsonl"

# NOT a real calibration value -- see module docstring point 2.
FOCAL_LENGTH_PX_PLACEHOLDER = 1000.0


class WildlifeCallbackState(app_callback_class):
    """Per-run state threaded through the GStreamer callback: config tables,
    the approach-vector tracker, the JSONL logger, and the alert controller.
    """

    def __init__(self, focal_length_px: float, log_path: Path, simulate_alerts: bool):
        super().__init__()
        self.species_table = load_species_table()
        self.zone_table = load_zone_table()
        self.approach_tracker = ApproachTracker()
        self.logger = DetectionLogger(log_path)
        self.focal_length_px = focal_length_px
        self.alert_controller = AlertController(
            led=LedBar(simulate=simulate_alerts),
            buzzer=Buzzer(simulate=simulate_alerts),
            oled=OledDisplay(simulate=simulate_alerts),
        )
        if simulate_alerts:
            print("[wildlife] Alerts running in SIMULATE mode -- no real LED/buzzer/OLED output.")


def _track_id(detection) -> int | None:
    ids = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
    return ids[0].get_id() if len(ids) == 1 else None


def app_callback(pad, info, user_data: WildlifeCallbackState):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()

    _format, _width, frame_height_px = get_caps_from_pad(pad)
    if frame_height_px is None:
        return Gst.PadProbeReturn.OK

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    alertable: list[RiskDetection] = []

    for detection in detections:
        label = detection.get_label()
        species = user_data.species_table.species.get(label)
        if species is None:
            continue  # "unlabeled" or anything not in config/species.yaml

        # HailoBBox height() is a 0..1 fraction of the frame; convert to px
        # for the thin-lens formula.
        bbox_height_px = detection.get_bbox().height() * frame_height_px
        if bbox_height_px <= 0:
            continue

        confidence = detection.get_confidence()
        track_id = _track_id(detection)
        distance_m = thin_lens_distance_for_species(bbox_height_px, species, user_data.focal_length_px)
        zone = classify_zone(distance_m, user_data.zone_table)

        # Every detection is logged regardless of approach direction or
        # alert selection (CLAUDE.md section 4: "All detections are still
        # logged").
        user_data.logger.log(
            species=label,
            confidence=confidence,
            zone_name=zone.name,
            distance_m=distance_m,
            gps_fix=None,  # GPS module not yet acquired (CLAUDE.md hardware table)
            track_id=track_id,
        )

        should_alert = (
            user_data.approach_tracker.should_alert(track_id, bbox_height_px) if track_id is not None else True
        )
        if should_alert:
            alertable.append(
                RiskDetection(track_id=track_id if track_id is not None else -1, label=label, confidence=confidence, distance_m=distance_m)
            )

    chosen = select_alert_detection(alertable, user_data.species_table)
    if chosen is not None:
        zone = classify_zone(chosen.distance_m, user_data.zone_table)
        # AlertController.trigger() blocks until LED+buzzer patterns finish
        # (led_bar.py / buzzer.py docstrings) -- fire on a background thread
        # so this GStreamer pad-probe callback never stalls the pipeline.
        threading.Thread(
            target=user_data.alert_controller.trigger,
            args=(zone,),
            kwargs={"species": chosen.label, "distance_m": chosen.distance_m},
            daemon=True,
        ).start()

    return Gst.PadProbeReturn.OK


def main():
    my_parser = argparse.ArgumentParser(add_help=False)
    my_parser.add_argument("--focal-length-px", type=float, default=FOCAL_LENGTH_PX_PLACEHOLDER)
    my_parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    my_parser.add_argument(
        "--live-alerts",
        action="store_true",
        help="Fire real LED/buzzer/OLED hardware. Default is simulate mode -- "
        "flip this on only once the circuit is soldered and wired (run "
        "scripts/test_led_bar.py etc. standalone first).",
    )
    known, remaining = my_parser.parse_known_args()

    # hailo_apps' own parser (built inside GStreamerDetectionApp) reads
    # sys.argv directly, so inject our defaults there rather than trying to
    # override an already-constructed argparse.Action.
    if not any(a.startswith("--hef-path") for a in remaining):
        remaining += ["--hef-path", str(DEFAULT_HEF_PATH)]
    if not any(a.startswith("--labels-json") for a in remaining):
        remaining += ["--labels-json", str(DEFAULT_LABELS_JSON)]
    sys.argv = [sys.argv[0], *remaining]

    if known.focal_length_px == FOCAL_LENGTH_PX_PLACEHOLDER:
        print(
            "[wildlife] WARNING: using the placeholder focal length "
            f"({FOCAL_LENGTH_PX_PLACEHOLDER}px), not a real calibration value. "
            "Distances/zones below are not trustworthy yet -- see module docstring."
        )

    user_data = WildlifeCallbackState(
        focal_length_px=known.focal_length_px,
        log_path=known.log_path,
        simulate_alerts=not known.live_alerts,
    )
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()


if __name__ == "__main__":
    main()
