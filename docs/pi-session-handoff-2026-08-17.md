# Session Handoff — August 17, 2026, in-car test

**For the next Claude Code session on the Pi (Termius/SSH, no monitor).** Read
this first, then `docs/car-test-2026-08-17.md` for the full step-by-step
procedure this continues. Deepansh is connecting via Termius from his phone,
SSH'd into the Pi over his phone hotspot — no monitor, no keyboard, phone
on-screen keyboard only.

## What's already done today

- Hardware check (before leaving the house): camera (imx219, detected fine),
  LED bar, buzzer, OLED all tested and confirmed working. OLED had dropped off
  the I2C bus (`0x3c` missing from `i2cdetect -y 1`) — reseating the connector
  fixed it, confirmed present and rendering correctly afterward. If it drops
  again under vehicle vibration, that's the known unresolved connector issue,
  not new.
- `git pull` done, `.hef` hash verified against `CLAUDE.md`'s recorded value
  — model is current, no action needed there.
- `vcgencmd get_throttled` was `0x0` (clean power) before disconnecting.
- SSH enabled and running as a systemd service (`sudo systemctl enable --now
  ssh`) — survives reboot/power-cycle, should already be active once you
  read this.
- Phone hotspot ("Deepansh's S25 Ultra") saved as a NetworkManager connection
  profile named `S25-hotspot` with `autoconnect-priority=10`, so the Pi
  should auto-join it once in range and off other known networks. If SSH
  connection fails, first check what IP the Pi actually got on the hotspot
  (check the phone's hotspot "connected devices" list) — the old home-WiFi IP
  (`10.0.0.93`) won't work once it's on the hotspot.
- `scripts/capture_calibration_photos.py` was updated: dropped a fixed
  `--shutter` value (produced solid-black frames in low light — bad idea,
  reverted), now uses `--exposure sport --awb daylight` on the
  `rpicam-still` call instead. This biases auto-exposure toward a faster
  shutter + more gain (less handheld blur) without hardcoding a shutter
  speed that can underexpose. Verified working with a live test shot after
  the camera was freshly mounted — sharp, correctly exposed, no blur.
- **A first calibration attempt (6 photos) was bad and should be deleted
  before the real run** — `~/calibration_photos/photo01-06.jpg` are test/
  accidental shots (indoor motion blur, and the camera briefly stuck in a
  pocket producing solid dark frames). Not checkerboard photos. Run:
  ```
  rm ~/calibration_photos/photo*.jpg
  ```
  before starting the real capture, so `calibrate_camera.py` doesn't ingest
  junk frames.

## Immediate next step

Camera should now be mounted in its final windshield position, car parked,
Aditya holding the checkerboard outside near the windshield at roughly
0.5-2m from the lens, varying angle/tilt/position (not flat-on/centered
every time). Once confirmed ready:

```
cd ~/bc-wildlife-dashcam
rm ~/calibration_photos/photo*.jpg   # clear the bad test shots first
python3 scripts/capture_calibration_photos.py
```

This takes 20 photos, ~4s apart, with a 3-2-1 terminal-bell countdown between
each so Deepansh/Aditya don't need to watch a screen once it starts — just
reposition the board on each beep.

## After capture: rest of `docs/car-test-2026-08-17.md`

- Step 4: run `scripts/calibrate_camera.py ~/calibration_photos
  --square-size-mm 23`, check reprojection error (<1.0px target), note the
  focal length (fx).
- Step 5: `scripts/run_wildlife_detection.py --focal-length-px <fx>
  --live-alerts` — only meaningful once real fx is in hand.
- Step 6 / after-test: log results in `docs/meeting_log.md` under today's
  date. Hard safety constraint still applies — screen/typing work only with
  the car parked.
