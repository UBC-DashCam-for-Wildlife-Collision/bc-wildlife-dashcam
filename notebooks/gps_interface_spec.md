# GPS Interface Specification
**Module:** u-blox NEO-M8N  
**Author:** Aditya Patel  
**Date:** May 13, 2026  
**Status:** Draft v1.0

---

## 1. UART Configuration

| Parameter | Value |
|---|---|
| Baud Rate | 9600 bps |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Format | 8N1 |
| Connection | NEO-M8N TX pin → Raspberry Pi GPIO 15 (RX) |
| Output Rate | 1 Hz (default) |

---

## 2. NMEA Sentence Parsed

Sentence type: GPRMC (Recommended Minimum Specific GPS Data)

This is the only sentence parsed. All other NMEA sentences output by the module are ignored.

Example raw sentence:

```
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
```

Field breakdown:

| Position | Example Value | Field | Used |
|---|---|---|---|
| 0 | $GPRMC | Sentence ID | No |
| 1 | 123519 | UTC Time (HHMMSS) | Yes |
| 2 | A | Status (A=valid, V=invalid) | Yes |
| 3 | 4807.038 | Latitude (DDMM.MMM) | Yes |
| 4 | N | N/S indicator | Yes |
| 5 | 01131.000 | Longitude (DDDMM.MMM) | Yes |
| 6 | E | E/W indicator | Yes |
| 7 | 022.4 | Speed over ground (knots) | No |
| 8 | 084.4 | Course over ground | No |
| 9 | 230394 | Date (DDMMYY) | Yes |
| 10 | 003.1,W | Magnetic variation | No |

---

## 3. Output Data Structure

This is the exact Python dictionary the GPS module hands to Deepansh's detection logger on every valid fix. This is the binding interface contract between the two sides of the pipeline.

```python
{
  "utc_timestamp": "2026-05-13T04:25:00Z",  # ISO 8601 format
  "latitude": 49.8801,                        # Decimal degrees, float
  "longitude": -119.4436                      # Decimal degrees, float
}
```

NMEA outputs latitude as DDMM.MMMM and must be converted to decimal degrees before logging. For latitude the degree prefix is 2 digits, for longitude it is 3 digits. Negative values apply for S and W directions.

---

## 4. Validation Rules

Before any GPS fix is passed to the logger the following must be true:

- Status field (position 2) must equal A — if V the sentence has no satellite lock and must be discarded
- Latitude and longitude fields must not be empty strings
- UTC timestamp must be parseable as a valid time

Any sentence failing these checks is silently dropped. The logger is never handed an invalid fix.

---

## 5. Current Draw

| Mode | Typical | Max | Voltage |
|---|---|---|---|
| Acquisition | 32mA | 67mA | 3.0V |
| Tracking continuous | 30mA | 67mA | 3.0V |
| Tracking power save 1Hz | 13mA | — | 3.0V |

Value used in power budget: 67mA worst-case max during continuous operation while driving.

Source: NEO-M8N Datasheet Section 4.3 Table 11 UBX-15031086

---

## 6. Notes

- GPS module is powered at 3.3V via the Pi's 3.3V GPIO rail
- Do not connect to 5V — the NEO-M8N is a 3.3V device and will be damaged
- Allow 30 to 60 seconds for first satellite acquisition on cold start — this is normal
- In the Okanagan highway test drive acquisition should be completed before the vehicle starts moving
