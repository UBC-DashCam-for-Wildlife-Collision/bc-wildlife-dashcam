# Interface Contract

**Between:** Deepansh Sabharwal (software) and Aditya Patel (hardware/electrical)
Last updated: June 25, 2026

This document defines the exact data formats and physical specifications that cross the boundary between Aditya's hardware responsibilities and Deepansh's software pipeline. Any change to these interfaces must be agreed by both parties and updated here before implementation.

---

## 1. GPS Data Stream

- **Owner:** Aditya
- **Consumer:** Deepansh (detection logger)
- **Module:** u-blox NEO-M8N
- **Transport:** gpsd daemon, Python gps module, parsed from GPRMC sentences
- **Update rate:** 1 Hz default (5 Hz if configurable via u-center)

**Output format:** Python dict per valid GPS fix, handed directly to the detection logger.

```python
{
    "utc_timestamp": "2026-05-13T04:25:00Z",   # ISO 8601
    "latitude": 49.8801,                         # Decimal degrees, float
    "longitude": -119.4436,                      # Decimal degrees, float, negative for W
    "speed_kmh": 97.2                            # Speed over ground, converted from knots
}
```

**Validation rules:** Status field must be `A` (valid fix). Latitude and longitude must not be empty. UTC timestamp must be parseable. Any sentence failing these checks is silently dropped. The logger never receives an invalid fix.

See [gps_interface_spec.md](gps_interface_spec.md) for full UART configuration and NMEA parsing details.

---

## 2. Camera Intrinsic Matrix

- **Owner:** Aditya
- **Consumer:** Deepansh (distance estimation)
- **Method:** OpenCV checkerboard calibration (`cv2.calibrateCamera`)
- **Camera:** Pi Camera Module 3 NoIR (Sony IMX708)

**Output format:** Two NumPy files.

| File | Shape | Contents |
|---|---|---|
| `camera_matrix.npy` | 3x3 | Intrinsic camera matrix (focal length in pixels, principal point) |
| `dist_coeffs.npy` | 1x5 | Distortion coefficients |

The focal length in pixels from the camera matrix is a hard dependency for both distance estimation methods (thin lens and TTC optical expansion). No distance estimation testing can begin until these files are delivered.

---

## 3. Stable Power Rail

- **Owner:** Aditya
- **Consumer:** Entire system
- **Source:** Vehicle 12V, stepped down to 5V

**Specification:**
- Voltage: 5.1V +/- 0.1V
- Current: 3A minimum under full load
- Full load defined as: Pi 5 + Hailo-8L + Camera Module 3 NoIR + GPS + LED bar + OLED + buzzer, all active simultaneously

Validated with all components active. Brownout or undervoltage will cause Pi 5 throttling, which directly degrades inference frame rate.

---

## 4. Vibration Characterization Report

- **Owner:** Aditya
- **Consumer:** Both (feeds into confidence threshold calibration)

**Output format:** CSV file.

| Column | Type | Description |
|---|---|---|
| `speed_kmh` | float | Vehicle speed at time of measurement |
| `detection_confidence_mean` | float | Mean detection confidence across frames |
| `detection_confidence_std` | float | Standard deviation of detection confidence |
| `class_label` | string | Species class measured |

This data quantifies how vehicle vibration at different speeds affects detection confidence, which informs whether confidence thresholds need speed-dependent adjustment.

**Delivery:** Phase 5 (validation), during road testing.
