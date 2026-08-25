#!/usr/bin/env bash
# Launcher for the live wildlife-detection pipeline, used by
# wildlife-detection.service (see docs/road-test-deployment.md). Not meant
# to be run by hand for a quick check -- use
#   source ~/hailo-rpi5-examples/venv_hailo_rpi_examples/bin/activate
#   python3 scripts/run_wildlife_detection.py -i rpi --live-alerts
# for that. This wrapper exists so systemd has one fixed command: activates
# the hailo_apps venv (not this repo's own venv -- it lacks gi/GStreamer/
# hailo bindings, see run_wildlife_detection.py's module docstring), then
# execs the pipeline with the road-test flags (full 8-LED bar, raised
# buzzer volume, real calibrated focal length auto-loaded from
# config/camera_matrix.npy).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
mkdir -p logs

source "$HOME/hailo-rpi5-examples/venv_hailo_rpi_examples/bin/activate"

exec python3 scripts/run_wildlife_detection.py \
    -i rpi \
    --live-alerts \
    --num-pixels "${WILDLIFE_NUM_PIXELS:-8}" \
    --buzzer-volume "${WILDLIFE_BUZZER_VOLUME:-0.6}" \
    --min-confidence "${WILDLIFE_MIN_CONFIDENCE:-0.6}" \
    --log-path "${WILDLIFE_LOG_PATH:-$REPO_ROOT/logs/detections.jsonl}"
