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
#
# --video-sink fakesink: there's no monitor in the car, so the preview
# window autovideosink would try to open is pointless anyway; fakesink
# avoids depending on a display sink under a headless systemd session.
# Detections are read from the pad-probe callback upstream of the display
# branch regardless of what the sink does, so this doesn't affect
# detection either way -- it's hygiene, not a fix for a real hang (the
# "XDG_RUNTIME_DIR is invalid" line some libcamera/picamera2 internals
# print is unrelated and benign -- confirmed it still prints even with
# fakesink, and does not block anything).
#
# -u / PYTHONUNBUFFERED=1: without this, redirected to a log file (not a
# tty), Python block-buffers stdout -- the log can sit empty for minutes
# even while the pipeline is working fine. This is what first looked like
# a hang on 2026-08-25 (systemd showed the service "active" with an empty
# stdout log and no detections, right after this service was first
# installed) -- turned out to be pure buffering, not a stuck pipeline:
# re-tested with unbuffered output and it reaches "picamera_process
# started" within seconds, and the shutdown handler still fires cleanly on
# stop. Keeping this is what makes that observable in real time instead of
# only in one batch at process exit.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
mkdir -p logs

source "$HOME/hailo-rpi5-examples/venv_hailo_rpi_examples/bin/activate"

# PYTHONUNBUFFERED (env var, not just -u) so it propagates into the
# picamera2 source's own subprocess too -- see the comment above.
export PYTHONUNBUFFERED=1

exec python3 -u scripts/run_wildlife_detection.py \
    -i rpi \
    --live-alerts \
    --num-pixels "${WILDLIFE_NUM_PIXELS:-8}" \
    --buzzer-volume "${WILDLIFE_BUZZER_VOLUME:-0.6}" \
    --min-confidence "${WILDLIFE_MIN_CONFIDENCE:-0.6}" \
    --log-path "${WILDLIFE_LOG_PATH:-$REPO_ROOT/logs/detections.jsonl}" \
    --video-sink "${WILDLIFE_VIDEO_SINK:-fakesink}"
