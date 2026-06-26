# GPS Interface Specification

**Module:** u-blox NEO-M8N
**Author:** Aditya Patel
**Last updated:** June 25, 2026
**Status:** Draft v1.1

---

## 1. UART Configuration

| Parameter | Value |
|---|---|
| Baud rate | 9600 bps |
| Data bits | 8 |
| Parity | None |
| Stop bits | 1 |
| Format | 8N1 |
| Connection | NEO-M8N TX → Raspberry Pi 5 GPIO 15 (RX) |
| Output rate | 1 Hz (default) |

---

## 2. NMEA Sentence Parsed

**Sentence type:** GPRMC (Recommended Minimum Specific GPS Data)

This is the only sentence parsed. All other NMEA sentences output by the module are ignored.

**Example raw sentence:**

```
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
```

**Field breakdown:**

| Position | Example | Field | Used |
|---|---|---|---|
| 0 | `$GPRMC` | Sentence ID | No |
| 1 | `123519` | UTC time (HHMMSS) | Yes |
| 2 | `A` | Status (A=valid, V=invalid) | Yes |
| 3 | `4807.038` | Latitude (DDMM.MMM) | Yes |
| 4 | `N` | N/S indicator | Yes |
| 5 | `01131.000` | Longitude (DDDMM.MMM) | Yes |
| 6 | `E` | E/W indicator | Yes |
| 7 | `022.4` | Speed over ground (knots) | Yes |
| 8 | `084.4` | Course over ground (degrees) | No |
| 9 | `230394` | Date (DDMMYY) | Yes |
| 10 | `003.1,W` | Magnetic variation | No |

Speed over ground (position 7) is parsed and converted from knots to km/h (`speed_kmh = knots * 1.852`). This value is used for GPS speed scaling of proximity zone thresholds and for TTC-based distance estimation.

---

## 3. Output Data Structure

Python dictionary handed to Deepansh's detection logger on every valid fix. This is the binding interface contract between Aditya's GPS module and Deepansh's software pipeline.

```python
{
    "utc_timestamp": "2026-05-13T04:25:00Z",   # ISO 8601
    "latitude": 49.8801,                         # Decimal degrees, float
    "longitude": -119.4436,                      # Decimal degrees, float, negative for W
    "speed_kmh": 97.2                            # Converted from knots, float
}
```

NMEA outputs latitude as DDMM.MMMM. Conversion to decimal degrees: the degree prefix is 2 digits for latitude, 3 digits for longitude. Negative values for S and W directions.

---

## 4. Validation Rules

Before any GPS fix is passed to the logger:

1. Status field (position 2) must equal `A`. If `V`, the sentence has no satellite lock and is discarded.
2. Latitude and longitude fields must not be empty strings.
3. UTC timestamp must be parseable as a valid time.
4. Speed field must be a valid float (default to 0.0 if missing but fix is otherwise valid).

Any sentence failing checks 1-3 is silently dropped. The logger never receives an invalid fix.

---

## 5. Current Draw

| Mode | Typical | Max | Voltage |
|---|---|---|---|
| Acquisition | 32 mA | 67 mA | 3.0V |
| Tracking continuous | 30 mA | 67 mA | 3.0V |
| Tracking power save 1 Hz | 13 mA | — | 3.0V |

Value used in power budget: 67 mA worst-case max during continuous operation while driving.

Source: NEO-M8N Datasheet Section 4.3, Table 11 (UBX-15031086).

---

## 6. Wiring Notes

- GPS module is powered at 3.3V via the Pi's 3.3V GPIO rail.
- Do not connect to 5V. The NEO-M8N is a 3.3V device and will be damaged at 5V.
- Allow 30-60 seconds for first satellite acquisition on cold start.
- In the Okanagan highway test, acquisition should be completed before the vehicle starts moving.
- GPS module is not yet acquired as of June 25, 2026. This is the only remaining hardware component.
