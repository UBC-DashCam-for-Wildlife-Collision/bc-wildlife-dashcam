# Road-test deployment (systemd)

Runs `scripts/run_wildlife_detection.py` unattended in the car: starts
automatically, survives a dropped SSH session (nothing needs to stay
attached), restarts itself if it crashes, and turns off the LED/buzzer/OLED
cleanly on stop (see the signal-handling section of
`scripts/run_wildlife_detection.py`'s docstring for why that needed a fix on
2026-08-22).

## One-time install (needs your password — I can't run `sudo` for you)

```bash
cd ~/bc-wildlife-dashcam
sudo cp scripts/wildlife-detection.service /etc/systemd/system/wildlife-detection.service
sudo systemctl daemon-reload
```

## Running it

```bash
# Start now (foreground-equivalent, runs until stopped):
sudo systemctl start wildlife-detection.service

# Watch it live:
journalctl -u wildlife-detection.service -f
# or: tail -f logs/wildlife-detection.stdout.log logs/wildlife-detection.stderr.log

# Stop (turns hardware off cleanly, see run_wildlife_detection.py):
sudo systemctl stop wildlife-detection.service

# Auto-start on every boot (only turn this on once you're actually doing a
# road test day -- it means live LED/buzzer/OLED output the moment the Pi
# powers up in the car):
sudo systemctl enable wildlife-detection.service
sudo systemctl disable wildlife-detection.service   # to undo
```

Detections still log to `logs/detections.jsonl` exactly as before — nothing
about the logging path changes under systemd.

## What the service runs

`scripts/run_wildlife_detection_road.sh`, which:
- activates `~/hailo-rpi5-examples/venv_hailo_rpi_examples` (not this repo's
  own venv — that one lacks the `gi`/GStreamer/`hailo` bindings)
- runs with `--live-alerts` (real hardware, not simulate mode)
- uses the full 8-LED bar and a raised buzzer volume (0.6) by default —
  matches what was tuned live on the bench 2026-08-22
- auto-loads the real calibrated focal length from
  `config/camera_matrix.npy` (no more placeholder warning, see
  `run_wildlife_detection.py`)

Override any of these per-run without editing files:

```bash
sudo systemctl edit wildlife-detection.service
# add under [Service]:
#   Environment=WILDLIFE_BUZZER_VOLUME=0.4
#   Environment=WILDLIFE_NUM_PIXELS=8
#   Environment=WILDLIFE_MIN_CONFIDENCE=0.6
```

## Verified 2026-08-25

Ran the launcher script directly (not yet through installed systemd, since
that step needs an interactive `sudo` password): camera pipeline started,
calibrated focal length auto-loaded correctly, `SIGTERM` produced a clean
shutdown log with no lingering process. Also stress-tested (20 trials, fake
GPIO backend) the case where a shutdown signal lands while a buzzer pattern
is still mid-loop — see `docs/meeting_log.md` Aug 25 entry for the bug this
caught and fixed.
