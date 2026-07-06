"""GPRMC NMEA sentence parser, per docs/gps_interface_spec.md.

This is pure string parsing -- no serial port access -- so it's fully
buildable and testable before the u-blox NEO-M8N module is acquired and
wired by Aditya. Once the module is wired (UART RX = GPIO 15, 3.3V), feed
its raw lines through `parse_gprmc`.

Only GPRMC sentences are parsed; all others are ignored (per spec section 2).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timezone


@dataclass(frozen=True)
class GpsFix:
    utc_timestamp: str  # ISO 8601
    latitude: float
    longitude: float
    speed_kmh: float


def _nmea_to_decimal(value: str, degree_digits: int, hemisphere: str) -> float:
    """Convert NMEA DDMM.MMMM / DDDMM.MMMM to signed decimal degrees."""
    degrees = int(value[:degree_digits])
    minutes = float(value[degree_digits:])
    decimal = degrees + minutes / 60.0
    if hemisphere in ("S", "W"):
        decimal = -decimal
    return decimal


def parse_gprmc(sentence: str) -> GpsFix | None:
    """Parse one GPRMC sentence into a GpsFix, or None if invalid/not GPRMC.

    Validation rules (spec section 4): status must be 'A', lat/lon must be
    non-empty, and the UTC timestamp must be parseable. Any failure here
    returns None silently -- the caller (detection logger) never sees an
    invalid fix.
    """
    sentence = sentence.strip()
    if "*" in sentence:
        sentence = sentence.split("*", 1)[0]  # drop checksum
    fields = sentence.split(",")
    if len(fields) < 10 or not fields[0].endswith("RMC"):
        return None

    _, utc_time, status, lat_raw, lat_hemi, lon_raw, lon_hemi, speed_knots, _course, utc_date = fields[:10]

    if status != "A":
        return None
    if not lat_raw or not lon_raw:
        return None

    try:
        hh, mm, ss = int(utc_time[0:2]), int(utc_time[2:4]), int(utc_time[4:6])
        dd, mo, yy = int(utc_date[0:2]), int(utc_date[2:4]), int(utc_date[4:6])
        # NMEA's 2-digit year is inherently ambiguous; windowing to 2000-2099
        # is correct for this system's real operating lifetime (2020s-2030s).
        full_year = 2000 + yy
        timestamp = datetime.combine(
            date(full_year, mo, dd), time(hh, mm, ss), tzinfo=timezone.utc
        )
    except (ValueError, IndexError):
        return None

    try:
        latitude = _nmea_to_decimal(lat_raw, 2, lat_hemi)
        longitude = _nmea_to_decimal(lon_raw, 3, lon_hemi)
    except (ValueError, IndexError):
        return None

    try:
        speed_kmh = float(speed_knots) * 1.852 if speed_knots else 0.0
    except ValueError:
        speed_kmh = 0.0

    return GpsFix(
        utc_timestamp=timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        latitude=latitude,
        longitude=longitude,
        speed_kmh=speed_kmh,
    )
