# Car Test Handoff — August 17, 2026

**Read this whole file before doing anything.** It supersedes
`docs/pi-session-handoff-2026-08-17.md` as the current status — that file is
still accurate for what it covers, this one carries the story forward to
where the session actually stalled. `docs/car-test-2026-08-17.md` is the
original step-by-step procedure both handoffs are executing.

**Where things stand right now: blocked on SSH connectivity, not on the
calibration or detection work itself.** Nothing past hardware setup has run
yet today.

---

## Session context

Deepansh is testing the system mounted in a car for the first time, with
Aditya on-site holding the checkerboard. No monitor or keyboard for the
Pi — everything goes through Termius on Deepansh's phone, over the phone's
own hotspot ("Deepansh's S25 Ultra"), since there's no home WiFi at the car.

**Hard safety constraint, still in force:** any screen-watching, typing, or
debugging happens only with the car parked. Nothing in this project involves
looking at a phone or laptop screen while the vehicle is moving.

---

## What's confirmed done and working

- **Checkerboard verified correct.** Official OpenCV 9x6-internal-corner
  pattern (A4), printed at 100% scale (not "fit to page"). Physically
  counted at **7 x 10 squares**, which is exactly right for a 9x6-corner
  board. Measured square size: **23mm**. This checks out mathematically —
  10 squares x 23mm = 230mm fits on A4's long 297mm edge with margin, so the
  print was not scaled down. Use `--square-size-mm 23` without
  re-verifying.
- **Pre-drive hardware check passed**, done before leaving the house:
  camera (imx219) detected fine, LED bar, buzzer, and OLED all tested and
  confirmed working individually. The OLED had dropped off the I2C bus
  (`0x3c` missing from `i2cdetect -y 1`) — this is the same known loose-
  connector issue from the Aug 12 session
  (`docs/meeting_log.md`), not new. Reseating the connector fixed it and it
  was confirmed present and rendering correctly before departure. **If it
  drops again under vehicle vibration today, that is the known unresolved
  issue, not a new bug** — the physical fix (reseat/resolder more
  permanently) still hasn't been done.
- **Model verified current.** `git pull` done, `.hef` SHA-256 checked
  against the value recorded in `CLAUDE.md` for the Aug 12 max-optimization
  compile. Matches — no action needed there.
- **Power confirmed clean before departure.** `vcgencmd get_throttled`
  returned `0x0` (no under-voltage or thermal throttling) before
  disconnecting. The Pi is running off a cigarette-lighter USB charger
  today, not the final in-vehicle 12V-to-5V regulator — if anything
  behaves strangely once testing resumes (random reboots, camera/Hailo
  dropping out, OLED misbehaving), **run `vcgencmd get_throttled` again
  first** before assuming it's a software bug. Non-zero means power, not
  code.
- **`scripts/capture_calibration_photos.py` written and tuned.** Auto-
  captures 20 photos with a terminal-bell countdown between shots (audible
  cue works over SSH with no screen needed — whoever holds the board just
  repositions on each beep). One real fix already made: an initial version
  used a fixed `--shutter` value that produced solid-black frames in low
  light; reverted to `--exposure sport --awb daylight` instead, which
  biases toward a faster shutter and more gain without hardcoding a value
  that can underexpose. Verified with one live test shot after the camera
  was freshly mounted — sharp, correctly exposed, no blur.
- **SSH made persistent.** Enabled as a systemd service
  (`sudo systemctl enable --now ssh`) so it survives reboot/power-cycle.
  Phone hotspot saved as a NetworkManager profile (`S25-hotspot`,
  `autoconnect-priority=10`) so the Pi should auto-join it when in range and
  off other known networks.
- **Bad test photos identified, not yet cleared.** Six accidental/junk
  frames sit in `~/calibration_photos/` (`photo01.jpg` through
  `photo06.jpg` — indoor motion blur, and a couple of solid-dark frames
  from the camera briefly being in a pocket). These are **not** real
  checkerboard photos and must be deleted before the real capture run, or
  `calibrate_camera.py` will ingest junk frames:
  ```
  rm ~/calibration_photos/photo*.jpg
  ```

## What has NOT happened yet

- The bad-photo cleanup above (queued, not executed)
- The real 20-photo calibration capture (`capture_calibration_photos.py`)
- Running `calibrate_camera.py` and getting a real reprojection error / fx
- Running `run_wildlife_detection.py --live-alerts` with a real focal length
- Any live-road or live-detection results
- Logging results in `docs/meeting_log.md`

**None of the actual test has run. The session stalled at connectivity,
right as the camera was mounted and everyone was ready to start capturing.**

---

## Current blocker: SSH connection lost

After the camera was mounted in its final position (which likely meant
moving the car, and possibly moving out of range of anything the Pi was
previously connected to), Termius on the phone could not reconnect to the
Pi. Attempted so far:

1. `ssh bc-dashcam@bc-dashcam.local` (mDNS hostname) — **failed**.
2. Direct IP was not yet tried as of this handoff — this is the next step.

### Troubleshooting path, in order

**Step 1 — check the phone's own hotspot "connected devices" list**
(in the phone's hotspot settings screen, not Termius). This tells you
immediately which of two very different problems this is:

**If the Pi shows up as a connected device:**
- Note its exact current IP from that list.
- Try that IP directly in Termius: `ssh bc-dashcam@<that-ip>` — do not
  rely on `.local` resolution working over a phone hotspot, it may not.
- Watch for a **host key changed / server identity warning** in Termius.
  Since the Pi's address changed, Termius may be silently blocking the
  connection behind a security prompt rather than failing loudly with a
  clear error. Accept/reset the host key if this appears.

**If the Pi does NOT show up as a connected device at all**, the Pi never
actually joined the hotspot. This is a different, more fundamental problem.
Possible causes, roughly in order of likelihood:
- The phone hotspot has **AP/client isolation** enabled (check
  Settings -> Hotspot -> Advanced on the phone) — some phones isolate
  connected devices from each other by default, which would prevent this
  even if the Pi did join.
- The Pi is still trying to reconnect to home WiFi instead of switching to
  the hotspot, if it's anywhere near the edge of that network's range.
- The hotspot itself timed out or was disabled by the phone's power-saving
  behavior before the Pi attempted to join.

If the Pi genuinely isn't reachable and there's no monitor/keyboard on hand
as a fallback, the pragmatic move is to **pause the remote session here**
rather than keep burning field time — reconnecting the old-fashioned way
(monitor + keyboard, or waiting until back in range of known WiFi) may be
faster than continuing to troubleshoot blind over a phone hotspot.

---

## Once reconnected: resume exactly here

```
cd ~/bc-wildlife-dashcam
git pull origin main
rm ~/calibration_photos/photo*.jpg
python3 scripts/capture_calibration_photos.py
```

Then continue with `docs/car-test-2026-08-17.md` steps 4-6:
calibrate (`--square-size-mm 23`, check reprojection error < 1.0px, note
fx), run the live pipeline (`--focal-length-px <fx> --live-alerts`), watch
for the things flagged in that doc's Step 6 (real road-perspective
detection quality, alert firing, whether the OLED holds its connection
under vibration), and log the full result in `docs/meeting_log.md` under
today's date — including this connectivity gap, since it's a real part of
today's story and worth knowing about before the next field session.

---

## For next time: the actual fix, not a workaround

This is the second time a phone-hotspot-based field connection has been
fragile (see also the earlier UBC visitor-network captive-portal issue
earlier in the project). The durable fix, not something to attempt mid-
session today: set the **Pi up as its own WiFi access point** instead of
joining whatever network is available (`hostapd` + `dnsmasq`). The phone
would connect *to* the Pi's network instead of the reverse, giving the Pi a
fixed, always-known IP (typically `192.168.4.1`) regardless of location.
This needs to be set up while the Pi still has normal access — worth doing
back home before the next field session, so this specific failure mode
stops recurring.
