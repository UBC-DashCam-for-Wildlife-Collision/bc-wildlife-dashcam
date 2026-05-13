# Interface Contract: Deepansh - Aditya

Last updated: May 2026

## GPS Data Stream
- Owner: Aditya
- Consumer: Deepansh
- Spec: Python dict per GPS fix: `{lat: float, lon: float, speed_kmh: float, utc: str (ISO 8601)}`
- Transport: gpsd daemon, Python gps module, 5 Hz update rate, GPRMC sentences
- Deadline: End Week 1, Month 1

## Camera Intrinsic Matrix
- Owner: Aditya
- Consumer: Deepansh
- Spec: Two numpy files: `camera_matrix.npy` (3x3), `dist_coeffs.npy` (1x5). Output of cv2.calibrateCamera.
- Deadline: End Week 4, Month 1

## Stable 5.1V Power Rail
- Owner: Aditya
- Consumer: System
- Spec: 5.1V +/- 0.1V at 3A minimum under full load (Pi 4 + Coral + camera + peripherals). Validated with all components active simultaneously.
- Deadline: End Week 3, Month 1

## Vibration Characterization Report
- Owner: Aditya
- Consumer: Both
- Spec: CSV file with columns: speed_kmh, detection_confidence_mean, detection_confidence_std per class.
- Deadline: End Week 2, Month 3
