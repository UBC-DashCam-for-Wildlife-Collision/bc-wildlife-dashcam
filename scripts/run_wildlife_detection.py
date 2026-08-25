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

Focal length: if config/camera_matrix.npy exists (real checkerboard
calibration -- see docs/meeting_log.md, Aug 22 2026 entry, 16 hand-picked
photos, 1.34px reprojection error), its fx/fy are loaded automatically and
used unless --focal-length-px overrides them. Only falls back to
FOCAL_LENGTH_PX_PLACEHOLDER (untrustworthy distances/zones -- see the
warning this prints) if that file is missing.
"""

import argparse
import os
import signal
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

from src.alerts.buzzer import DEFAULT_VOLUME as DEFAULT_BUZZER_VOLUME  # noqa: E402
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
CAMERA_MATRIX_PATH = REPO_ROOT / "config" / "camera_matrix.npy"

# NOT a real calibration value -- only used if CAMERA_MATRIX_PATH is missing.
FOCAL_LENGTH_PX_PLACEHOLDER = 1000.0


def _load_calibrated_focal_length_px() -> float | None:
    """Average of fx/fy from config/camera_matrix.npy, or None if absent."""
    if not CAMERA_MATRIX_PATH.exists():
        return None
    import numpy as np

    camera_matrix = np.load(CAMERA_MATRIX_PATH)
    return float((camera_matrix[0, 0] + camera_matrix[1, 1]) / 2)

# hailo_apps' own detection_pipeline.py hardcodes its NMS score threshold at
# 0.3 (not exposed as a CLI flag) -- too permissive on its own, confirmed on
# the bench 2026-08-22: pointed at an ordinary indoor desk (mouse, fingers,
# keyboard, no wildlife in frame), it fired constant low-confidence
# detections across every species class. This is a second, stricter gate
# applied here in the project's own callback, after the Hailo pipeline's
# NMS has already run.
DEFAULT_MIN_CONFIDENCE = 0.6


class WildlifeCallbackState(app_callback_class):
    """Per-run state threaded through the GStreamer callback: config tables,
    the approach-vector tracker, the JSONL logger, and the alert controller.
    """

    def __init__(
        self,
        focal_length_px: float,
        log_path: Path,
        simulate_alerts: bool,
        num_pixels: int = 1,
        buzzer_volume: float = DEFAULT_BUZZER_VOLUME,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ):
        super().__init__()
        self.species_table = load_species_table()
        self.zone_table = load_zone_table()
        self.approach_tracker = ApproachTracker()
        self.logger = DetectionLogger(log_path)
        self.focal_length_px = focal_length_px
        self.min_confidence = min_confidence
        self.alert_controller = AlertController(
            led=LedBar(simulate=simulate_alerts, num_pixels=num_pixels),
            buzzer=Buzzer(simulate=simulate_alerts, volume=buzzer_volume),
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

        confidence = detection.get_confidence()
        if confidence < user_data.min_confidence:
            continue  # below our own stricter gate -- see DEFAULT_MIN_CONFIDENCE

        # HailoBBox height() is a 0..1 fraction of the frame; convert to px
        # for the thin-lens formula.
        bbox_height_px = detection.get_bbox().height() * frame_height_px
        if bbox_height_px <= 0:
            continue

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


def _shutdown_alerts(user_data: "WildlifeCallbackState") -> None:
    """Force LED/buzzer/OLED off. Idempotent -- safe to call more than once
    (e.g. once from a signal handler, once again from the finally safety net).

    Independent try/except per device: the OLED's I2C connector is known to
    drop under vibration (docs/meeting_log.md, Aug 12 and Aug 22 entries) --
    one device raising here must not skip turning off the other two.
    """
    print("[wildlife] Shutting down -- turning off LED/buzzer/OLED.", flush=True)
    try:
        user_data.alert_controller.led.off()
    except Exception as exc:
        print(f"[wildlife] LED shutdown failed: {exc}", flush=True)
    try:
        user_data.alert_controller.buzzer.off()
        user_data.alert_controller.buzzer.cleanup()
    except Exception as exc:
        print(f"[wildlife] Buzzer shutdown failed: {exc}", flush=True)
    try:
        user_data.alert_controller.oled.clear()
    except Exception as exc:
        print(f"[wildlife] OLED shutdown failed: {exc}", flush=True)
    print("[wildlife] Shutdown complete.", flush=True)


def _force_exit_soon(delay_s: float = 3.0) -> None:
    """Guarantee the process actually dies shortly after a shutdown signal.

    Confirmed on the bench 2026-08-22: even after hardware cleanup runs and
    control unwinds back out of app.run(), the OS process can linger
    (non-daemon camera/GStreamer worker threads keep it alive), which blocks
    the next run from acquiring the camera/Hailo device. Hardware is already
    safe by the time this timer is started (_shutdown_alerts runs first), so
    this is just a deadline for the process itself to be gone.
    """
    timer = threading.Timer(delay_s, lambda: os._exit(0))
    timer.daemon = True
    timer.start()


def main():
    my_parser = argparse.ArgumentParser(add_help=False)
    my_parser.add_argument(
        "--focal-length-px",
        type=float,
        default=None,
        help="Override the focal length used for distance estimation. Default: "
        f"auto-load fx/fy from {CAMERA_MATRIX_PATH.relative_to(REPO_ROOT)} if present, "
        f"else fall back to the untrustworthy {FOCAL_LENGTH_PX_PLACEHOLDER}px placeholder.",
    )
    my_parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    my_parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Drop detections below this confidence, applied on top of the "
        f"Hailo pipeline's own (looser, 0.3) NMS threshold. Default {DEFAULT_MIN_CONFIDENCE}.",
    )
    my_parser.add_argument(
        "--live-alerts",
        action="store_true",
        help="Fire real LED/buzzer/OLED hardware. Default is simulate mode -- "
        "flip this on only once the circuit is soldered and wired (run "
        "scripts/test_led_bar.py etc. standalone first).",
    )
    my_parser.add_argument(
        "--num-pixels",
        type=int,
        default=1,
        help="LED pixel count. Default 1 for the current single-LED bench "
        "circuit; set to the full bar's count once that's soldered.",
    )
    my_parser.add_argument(
        "--buzzer-volume",
        type=float,
        default=DEFAULT_BUZZER_VOLUME,
        help="Buzzer PWM duty cycle, 0.0-1.0 (see src/alerts/buzzer.py). "
        f"Default {DEFAULT_BUZZER_VOLUME} -- full volume (1.0) is ear-splitting indoors.",
    )
    my_parser.add_argument(
        "--video-sink",
        type=str,
        default=None,
        help="Override hailo_apps' GStreamer preview-window sink (hardcoded to "
        "'autovideosink' in the vendored library, no CLI flag of its own -- "
        "see run_wildlife_detection_road.sh). Pass 'fakesink' for any "
        "headless/unattended run: there's no monitor to preview to anyway, "
        "and detections are read from the pad-probe callback upstream of the "
        "display branch regardless of what the sink does. Not a fix for a "
        "hang -- see run_wildlife_detection_road.sh's comments on the "
        "2026-08-25 stdout-buffering false alarm this was first mistaken for.",
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

    if known.focal_length_px is None:
        calibrated = _load_calibrated_focal_length_px()
        if calibrated is not None:
            known.focal_length_px = calibrated
            print(
                f"[wildlife] Using calibrated focal length from "
                f"{CAMERA_MATRIX_PATH.relative_to(REPO_ROOT)}: {calibrated:.2f}px"
            )
        else:
            known.focal_length_px = FOCAL_LENGTH_PX_PLACEHOLDER
            print(
                "[wildlife] WARNING: using the placeholder focal length "
                f"({FOCAL_LENGTH_PX_PLACEHOLDER}px), not a real calibration value. "
                "Distances/zones below are not trustworthy yet -- see module docstring."
            )

    user_data = WildlifeCallbackState(
        focal_length_px=known.focal_length_px,
        log_path=known.log_path,
        simulate_alerts=not known.live_alerts,
        num_pixels=known.num_pixels,
        buzzer_volume=known.buzzer_volume,
        min_confidence=known.min_confidence,
    )

    app = GStreamerDetectionApp(app_callback, user_data)

    if known.video_sink is not None:
        app.video_sink = known.video_sink
        print(f"[wildlife] Overriding GStreamer preview sink -> {known.video_sink}")

    # A plain try/finally around app.run() does NOT reliably fire: confirmed
    # on the bench 2026-08-22 that hailo_apps' own SIGINT handler
    # (registered inside GStreamerDetectionApp.__init__, see
    # gstreamer_app.py) tears the process down without ever returning
    # control to our finally block, and SIGTERM (what plain `kill <pid>`
    # sends) has no handler installed anywhere and kills the process
    # immediately -- either way the WS2812B LEDs stayed latched at their
    # last color and the buzzer's software-PWM pin stayed stuck until
    # forced off manually. Fix: chain our own handler in *front* of
    # whatever hailo_apps does, so hardware cleanup runs synchronously as
    # the very first thing on the signal, not something we hope happens on
    # the way out.
    existing_sigint_handler = signal.getsignal(signal.SIGINT)

    def _handle_sigint(signum, frame):
        _shutdown_alerts(user_data)
        _force_exit_soon()
        if callable(existing_sigint_handler):
            existing_sigint_handler(signum, frame)
        else:
            sys.exit(0)

    def _handle_sigterm(signum, frame):
        _shutdown_alerts(user_data)
        _force_exit_soon()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    try:
        app.run()
    finally:
        # Safety net for the normal-exit/exception path; _shutdown_alerts
        # is idempotent so this is harmless if the signal handlers above
        # already ran it.
        _shutdown_alerts(user_data)


if __name__ == "__main__":
    main()
